# Module 1 — Kubernetes foundations

Module 1 gives you the mental model and the muscle memory you need for every
later module: containers and images, `kubectl`, Pods, Deployments, Services,
and Namespaces. It targets the **KCNA** track but everything here is load-
bearing for CKA, CKAD, and CKS, so resist the urge to skim.

## Learning objectives

1. Explain how containers relate to images, registries, and the OCI runtime,
   and how Kubernetes schedules those containers into Pods.
2. Drive `kubectl` confidently: `get`, `describe`, `logs`, `exec`, `apply`,
   `delete`, output formats, and label selectors.
3. Create and inspect a Pod, and explain its lifecycle states and restart
   policy.
4. Deploy, scale, update, and roll back a Deployment backed by a ReplicaSet.
5. Expose workloads with a Service and resolve them over cluster DNS.
6. Organise work into Namespaces and select resources by labels.

## Key concepts

- **Container**: an isolated process — its own filesystem, cgroup limits, and
  namespaces — built from an image. Kubernetes schedules containers, but the
  unit of scheduling is the Pod, not the container.
- **Image and registry**: an image is a read-only filesystem snapshot plus
  metadata, stored as layers in a registry (Docker Hub, quay.io, a private
  registry). `nginx:stable-alpine` is `name:tag`; tags are mutable, digests
  (`@sha256:...`) are not — a point Module 4 returns to.
- **Runtime**: the component that actually runs containers. Modern clusters
  use `containerd` via the CRI; you talk to it with `crictl`, never by
  reaching inside a running container's namespaces.
- **Pod**: the smallest deployable unit — one or more containers sharing a
  network namespace and optionally storage. Containers in a Pod always land on
  the same node and can talk on `localhost`.
- **Pod lifecycle**: a Pod passes through `Pending`, `Running`, `Succeeded` or
  `Failed`, and can sit in `CrashLoopBackOff` while a container keeps
  restarting. `restartPolicy: Always|OnFailure|Never` governs that.
- **`kubectl`**: the CLI that talks to `kube-apiserver` over HTTPS. It reads
  your kubeconfig, which holds clusters, users, and contexts; `kubectl config
  use-context` switches between them.
- **Declarative vs. imperative**: `kubectl create` and `kubectl run` build
  objects imperatively; `kubectl apply -f manifest.yaml` reconciles desired
  state — the way real workflows work, and the way the grader checks your
  work.
- **Label**: an arbitrary key/value pair on an object (`app=web`,
  `tier=backend`). Selectors filter on them, and Services, Deployments, and
  NetworkPolicies all select targets by label.
- **Deployment**: a controller that declares desired replicas of a Pod
  template. It owns a ReplicaSet, which owns the Pods, and it gives you
  scaling, rolling updates, and rollbacks for free.
- **Rolling update**: the default Deployment strategy. `maxUnavailable` and
  `maxSurge` control how many Pods may be down and how many extra may exist
  while a new ReplicaSet rolls in; `kubectl rollout status` tracks it.
- **Service**: a stable virtual IP (ClusterIP) in front of a label-selected
  set of Pods. Types are `ClusterIP` (default), `NodePort`, `LoadBalancer`,
  and `ExternalName`; Pods are found via `Endpoints`.
- **Cluster DNS**: CoreDNS resolves `service.namespace.svc.cluster.local`.
  A Service named `web-svc` in namespace `dev` is reachable from anywhere in
  the cluster as `web-svc.dev.svc.cluster.local`.
- **Namespace**: a virtual cluster for grouping and isolating objects —
  resource limits, quotas, RBAC, and NetworkPolicies all bind to a namespace.
  `kubectl get ns` lists them; `default`, `kube-system`, and `kube-public` are
  the built-ins.

## Hands-on exercises

All exercises assume `kubectl` reaches a running cluster (`kubectl get nodes`
shows Ready).

### Exercise 1 — Verify tooling and cluster

- Task: confirm the client and server versions, list your contexts and nodes.
- Expected outcome: `kubectl version` prints client and server versions,
  `kubectl config get-contexts` shows your active context, and nodes are
  `Ready`.

```sh
kubectl version
kubectl config get-contexts
kubectl get nodes -o wide
```

- Verification:

```sh
kubectl cluster-info
kubectl get nodes
```

### Exercise 2 — Run a Pod, imperatively then declaratively

- Task: start an nginx Pod with `kubectl run`, inspect it, then delete it and
  recreate the same Pod from a YAML manifest with `kubectl apply`.
- Expected outcome: the Pod named `hello` reaches `Running`, and the YAML-born
  Pod shows the same phase and the expected image.

```sh
kubectl run hello --image=nginx:stable-alpine --restart=Never
kubectl get pod hello -o wide
kubectl delete pod hello
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: hello
  labels:
    app: hello
spec:
  containers:
    - name: nginx
      image: nginx:stable-alpine
EOF
kubectl get pod hello -o wide
```

- Verification (must print `Running` twice):

```sh
kubectl get pod hello -o jsonpath='{.status.phase}{"\n"}'
kubectl logs hello
```

### Exercise 3 — Deploy, scale, and roll back

- Task: create a Deployment `web` with 3 replicas, scale it up to 5, then set a
  new image and watch the rollout; finally undo to the previous revision.
- Expected outcome: `kubectl rollout status deployment/web` reports success
  each time, `kubectl rollout history` shows revisions, and `undo` restores
  the earlier image.

```sh
kubectl create deployment web --image=nginx:stable-alpine --replicas=3
kubectl scale deployment/web --replicas=5
kubectl set image deployment/web nginx=nginx:stable-alpine --record
kubectl rollout status deployment/web
kubectl rollout history deployment/web
kubectl rollout undo deployment/web
kubectl rollout status deployment/web
```

- Verification (5 pods, then the rolled-back image):

```sh
kubectl get deployments,replicasets,pods -l app=web
kubectl get deployment web -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

### Exercise 4 — Expose the Deployment with a Service

- Task: expose `web` on port 80 as a ClusterIP Service named `web-svc`, then
  confirm the Endpoints track the Pods and DNS resolves the name.
- Expected outcome: `kubectl get svc web-svc` shows a ClusterIP; Endpoints has
  5 IPs matching the Pods; a curl from inside a Pod to `web-svc:80` returns
  nginx HTML.

```sh
kubectl expose deployment web --name=web-svc --port=80 --target-port=80
kubectl get svc web-svc -o wide
kubectl get endpoints web-svc
kubectl exec deployment/web -- sh -c 'wget -qO- http://web-svc:80/ | head -1'
```

- Verification (three IPs listed, matching pod IPs):

```sh
kubectl get endpoints web-svc
kubectl get pods -l app=web -o wide
```

### Exercise 5 — Namespaces and label selectors

- Task: create namespace `dev`, deploy an `api` Deployment into it with the
  label `tier=backend`, then list by namespace and by label.
- Expected outcome: `kubectl get all -n dev` shows the Deployment, ReplicaSet,
  and 2 Pods; the `-l tier=backend` selector returns exactly them.

```sh
kubectl create namespace dev
kubectl create deployment api --image=nginx:stable-alpine -n dev --replicas=2
kubectl label deployment api tier=backend -n dev
kubectl get all -n dev
kubectl get deployments -n dev -l tier=backend --show-labels
```

- Verification (two ready pods in `dev`, none in `default`):

```sh
kubectl get pods -n dev --show-labels
kubectl get pods -n default --show-labels
```

## Test yourself

When you can do Exercises 1–5 without the book, sit a simulator attempt:

- **Bank**: `banks/kcna`
- **First pass**: **Training** mode, `focus_domain = kubernetes-fundamentals` —
  read the explanation for every question, right or wrong.
- **Second pass**: **Mastery** mode, same domain, timed.
- **Third pass (optional)**: **Training**, `focus_domain = containers`, to
  close the container-imaging gaps before Module 2.
- Aim for 80%+ on the Mastery pass before starting Module 2; below that, redo
  Exercises 2–4, which carry most of the mechanics.

## See also

- KCNA certification page on linuxfoundation.org (referenced by name).
- [Module 2 — Administration](02-administration.md) — next: the control plane,
  kubeadm, etcd, and the CKA track.
