# Module 2 — Administration

Module 2 is the **CKA** track: the control plane, kubeadm installation,
etcd backup and restore, node management, scheduling, RBAC, storage, and
troubleshooting. You will work against a real cluster, because the hardest
parts of this exam are the ones you can only learn by doing: draining a node,
taking an etcd snapshot, and reading a `CrashLoopBackOff` correctly.

## Learning objectives

1. Describe every control plane and node component and what it does, and
   inspect the live control plane on your cluster.
2. Install a cluster with `kubeadm` and explain join tokens, static pods, and
   the kubeconfig that ties it together.
3. Back up and restore `etcd`, the single source of truth for cluster state.
4. Perform node maintenance safely: cordon, drain, uncordon, and understand
   what an upgrade touches.
5. Control pod placement with `nodeSelector`, `nodeName`, taints and
   tolerations, and affinity rules.
6. Grant least-privilege permissions with RBAC and provision persistent
   storage through PVs, PVCs, and StorageClasses.
7. Troubleshoot a failing cluster methodically: pods, services, DNS, and the
   kubelet.

## Key concepts

- **Control plane**: `kube-apiserver` is the front door every `kubectl` call
  hits; `etcd` stores all state; `kube-scheduler` places Pods; the controller
  managers reconcile desired state. On kubeadm clusters these run as static
  Pods under `/etc/kubernetes/manifests` — delete the manifest and the kubelet
  removes the Pod.
- **Node components**: `kubelet` registers the node and runs Pods the
  scheduler chooses; `kube-proxy` implements Service routing with iptables or
  IPVS; the container runtime (`containerd`/CRI) actually starts containers.
- **kubeadm**: `kubeadm init` boots a control plane (with
  `--control-plane-endpoint`, `--apiserver-cert-extra-sans`), writes
  `/etc/kubernetes/admin.conf`, and prints a `kubeadm join` token; control
  planes are extended with `kubeadm join --control-plane`, workers with plain
  `kubeadm join`.
- **kubeconfig**: YAML with `clusters`, `users`, `contexts`, and a
  `current-context`. Context = cluster + user + namespace. `kubectl config
  view`, `--kubeconfig`, and `KUBECONFIG` select which one you act on.
- **etcd**: distributed key-value store holding every object. It must be
  backed up with `ETCDCTL_API=3 etcdctl snapshot save` using `--cacert`,
  `--cert`, `--key` from the static-pod certificates, and restored with
  `snapshot restore` into a fresh data dir — never restore onto a live member.
- **Node maintenance**: `kubectl cordon` marks a node unschedulable for new
  Pods; `kubectl drain --ignore-daemonsets --delete-emptydir-data` evicts
  existing ones; `uncordon` reverses it. Drains are the safe shape of an
  upgrade or a reboot.
- **Scheduling**: `nodeSelector` pins to a label, `nodeName` overrides the
  scheduler entirely, taints repel (no toleration = no placement), tolerations
  opt in, and `nodeAffinity`/`podAffinity` express soft or hard placement
  rules.
- **Resource management**: `requests` guarantee capacity (the scheduler uses
  them), `limits` cap usage and can trigger eviction; `LimitRange` and
  `ResourceQuota` police a namespace. Scheduling only works if requests fit
  the node's allocatable.
- **RBAC**: `Role`/`ClusterRole` define verbs on resources, bindings attach
  them to users, groups, or ServiceAccounts (`RoleBinding`/`ClusterRoleBinding`).
  `kubectl auth can-i` proves what a principal can do — always test with it.
- **ServiceAccount**: the identity a Pod runs with. Its token authenticates to
  the API; bind a ClusterRole like `view` if the workload needs API access,
  and leave it unbound otherwise.
- **Storage**: `PersistentVolume` is cluster storage, `PersistentVolumeClaim`
  is a request for it, `StorageClass` provisions PVs dynamically
  (`provisioner`, `reclaimPolicy`, `volumeBindingMode`). PVCs bind to PVs by
  access mode and capacity; `volumeBindingMode: WaitForFirstConsumer` fixes
  zone pinning for topology-aware storage.
- **Static Pods vs. DaemonSets**: static Pods are written by the kubelet from
  files; DaemonSets are API objects that put one Pod on every node. Confusing
  the two breaks node-level troubleshooting.
- **Troubleshooting ladder**: start at the object — `describe` events, `logs`,
  `exec` — then the Service (`endpoints`), then DNS (`kubectl exec ... nslookup
  svc`), then the node (`journalctl -u kubelet`, `crictl ps`), then the
  control plane (`kubectl get componentstatuses`, apiserver logs).

## Hands-on exercises

All exercises assume admin access to a kubeadm-based cluster (kind/k3s work
for most; kubeadm is needed where noted).

### Exercise 1 — Inspect the control plane and kubelet health

- Task: list the control plane Pods, find the static-pod manifest directory,
  and check the kubelet service on a node.
- Expected outcome: `kube-system` shows `kube-apiserver`, `etcd`,
  `kube-controller-manager`, and `kube-scheduler` as Pods; the manifests live
  at `/etc/kubernetes/manifests`; `systemctl status kubelet` is active.

```sh
kubectl get pods -n kube-system -o wide
kubectl get nodes
kubectl describe node <node> | sed -n '/Kubelet/,/Taints/p'
kubectl logs -n kube-system kube-apiserver-<node> --tail=10
```

- Verification:

```sh
kubectl get pods -n kube-system -l component=kube-apiserver
kubectl get componentstatuses
```

### Exercise 2 — Back up and restore etcd

- Task: snapshot etcd to a local file, then restore it into a fresh data
  directory and check the snapshot metadata.
- Expected outcome: `etcdctl snapshot save` writes a non-empty snapshot and
  `snapshot status` reports the expected member count and revision.
  (A full in-place restore swaps the etcd static-pod manifest to point at the
  restored directory — do this in a throwaway cluster first.)

```sh
export ETCDCTL_API=3
kubectl -n kube-system get pod etcd-<node> -o jsonpath='{.spec.containers[0].command}' | tr ' ' '\n' | grep -E 'cacert|cert|key'
ETCD_CA=$(kubectl -n kube-system get pod etcd-<node> -o jsonpath='{.spec.containers[0].command}' | tr ' ' '\n' | grep cacert | cut -d= -f2)
ETCD_CERT=$(kubectl -n kube-system get pod etcd-<node> -o jsonpath='{.spec.containers[0].command}' | tr ' ' '\n' | grep cert= | cut -d= -f2)
ETCD_KEY=$(kubectl -n kube-system get pod etcd-<node> -o jsonpath='{.spec.containers[0].command}' | tr ' ' '\n' | grep key= | cut -d= -f2)
kubectl -n kube-system exec etcd-<node> -- sh -c "ETCDCTL_API=3 etcdctl --cacert=$ETCD_CA --cert=$ETCD_CERT --key=$ETCD_KEY snapshot save /tmp/snapshot.db"
kubectl -n kube-system cp etcd-<node>:/tmp/snapshot.db ./snapshot.db
```

- Verification:

```sh
kubectl -n kube-system exec etcd-<node> -- sh -c "ETCDCTL_API=3 etcdctl --cacert=$ETCD_CA --cert=$ETCD_CERT --key=$ETCD_KEY snapshot status /tmp/snapshot.db -w json"
ls -l snapshot.db
```

### Exercise 3 — Grant least-privilege RBAC

- Task: create a ServiceAccount `deployer` in namespace `dev`, give it only
  the rights to get, list, and create Deployments there, and prove what it
  can and cannot do.
- Expected outcome: `kubectl auth can-i --as=system:serviceaccount:dev:deployer
  create deployments -n dev` returns `yes`; `... delete deployments -n dev`
  returns `no`.

```sh
kubectl create namespace dev
kubectl create serviceaccount deployer -n dev
kubectl -n dev apply -f - <<'EOF'
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: deployment-manager
  namespace: dev
rules:
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "create"]
EOF
kubectl -n dev apply -f - <<'EOF'
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: deployer-deployments
  namespace: dev
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: deployment-manager
subjects:
  - kind: ServiceAccount
    name: deployer
    namespace: dev
EOF
```

- Verification:

```sh
kubectl auth can-i --as=system:serviceaccount:dev:deployer create deployments -n dev
kubectl auth can-i --as=system:serviceaccount:dev:deployer delete deployments -n dev
kubectl auth can-i --as=system:serviceaccount:dev:deployer create deployments -n default
```

### Exercise 4 — Cordon, drain, and control placement

- Task: mark a node unschedulable, drain it, place a workload on the surviving
  node with a taint and toleration, then restore the node.
- Expected outcome: after `cordon` the node reports `SchedulingDisabled`; a
  tolerating Pod lands on the tainted node while a plain Pod does not; after
  `uncordon` the node accepts workloads again.

```sh
kubectl cordon <node>
kubectl get nodes
kubectl drain <node> --ignore-daemonsets --delete-emptydir-data
kubectl uncordon <node>
kubectl taint nodes <node> app=stateful:NoSchedule
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: on-tainted
spec:
  containers:
    - name: nginx
      image: nginx:stable-alpine
  tolerations:
    - key: app
      operator: Equal
      value: stateful
      effect: NoSchedule
EOF
kubectl delete pod on-tainted
kubectl taint nodes <node> app=stateful:NoSchedule-
```

- Verification (Pod reports the tainted node; node is schedulable again):

```sh
kubectl get node <node> -o jsonpath='{.spec.unschedulable}'
kubectl get pod on-tainted -o wide
kubectl get nodes
```

### Exercise 5 — Provision storage and pin a workload

- Task: create a StorageClass-backed PVC, a Pod that mounts it, and confirm a
  file written by the Pod survives a restart.
- Expected outcome: the PVC reaches `Bound`, the Pod starts with the volume at
  `/data`, and a marker file persists across `kubectl delete pod`.

```sh
kubectl create namespace storage-lab
kubectl -n storage-lab apply -f - <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-claim
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 1Gi
EOF
kubectl -n storage-lab apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: writer
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "echo marker > /data/marker && sleep 3600"]
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: data-claim
EOF
kubectl -n storage-lab exec writer -- cat /data/marker
```

- Verification (PVC `Bound`; file survives a re-run):

```sh
kubectl get pvc -n storage-lab
kubectl -n storage-lab delete pod writer --force --grace-period=0
kubectl -n storage-lab apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: reader
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "cat /data/marker"]
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: data-claim
EOF
kubectl -n storage-lab logs reader
```

## Test yourself

When you can do Exercises 1–5 without the book, sit simulator attempts on
`banks/cka`:

- **First pass**: **Training**, `focus_domain = cluster-architecture-installation`.
- **Second pass**: **Mastery**, `focus_domain = troubleshooting` — the exam's
  biggest domain (30%).
- **Third pass**: **Mastery**, `focus_domain = workloads-scheduling`.
- **Final pass**: full-bank **Mastery** on `banks/cka`, timed to the bank's
  `duration_minutes`.

Troubleshooting is the domain the report will ding most often — drill it with
focused Mastery attempts and re-run Exercise 1's describe/logs ladder whenever
it shows up as a weakness.

## See also

- CKA certification page on linuxfoundation.org (referenced by name).
- [Module 3 — Application development](03-application-development.md) — next:
  the CKAD track.
