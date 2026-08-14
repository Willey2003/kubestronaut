# Module 3 — Application development

Module 3 is the **CKAD** track: designing and running applications on
Kubernetes — multi-container Pods, ConfigMaps and Secrets, probes, rollouts,
Services and Ingress, and PVC-backed storage. Where Module 2 ran the cluster,
this module builds and ships applications on it.

## Learning objectives

1. Design multi-container Pods using init, sidecar, and adapter patterns with
   a shared filesystem or loopback network.
2. Inject configuration with ConfigMaps and Secrets — as environment, as
   files, and immutable.
3. Wire liveness, readiness, and startup probes and explain what each restart
   or traffic-cut actually means.
4. Perform rolling updates, pause/unpause, roll back, and scale with
   `kubectl rollout` and the HorizontalPodAutoscaler.
5. Expose applications through Services, Ingress, and cluster DNS, and
   understand Endpoints and headless Services.
6. Persist application data through PVCs and pick the right volume type for
   the job.

## Key concepts

- **Pod containers**: containers in one Pod share a network namespace
  (`localhost` works) and can share volumes. `initContainers` run to
  completion before the main containers start — perfect for provisioning.
- **Init containers**: declared separately in the Pod spec, they run in order,
  and the main container only starts after every one exits 0. Failures rerun
  them (unless `restartPolicy: Never`). Used for waiting on dependencies or
  seeding data.
- **Sidecar**: a second, long-running container that serves the main one —
  a log-shipper tailing a shared volume, a proxy fronting a legacy binary, an
  adapter transforming metrics. Same Pod, same node, shared fate.
- **ConfigMap**: a namespace-scoped map of config data. Reference it as
  environment (`valueFrom.configMapKeyRef`), as files in a volume, or
  `--from-literal/--from-file` at creation. Changes propagate to volume mounts
  within ~1 minute, but not to env vars without a restart.
- **Secret**: like a ConfigMap but base64-encoded and treated as sensitive.
  Mount as files or env; `immutable: true` blocks updates (good for security
  and watch traffic). Prefer mounted files over env for anything long-lived.
- **Probes**: `livenessProbe` restarts a dead container, `readinessProbe`
  removes a Pod from Service Endpoints until ready, `startupProbe` gates the
  other two for slow starters. Handlers: `exec`, `httpGet`, `tcpSocket`;
  tune `initialDelaySeconds`, `periodSeconds`, `timeoutSeconds`,
  `successThreshold`, `failureThreshold`.
- **Deployment strategies**: `RollingUpdate` (default) with `maxUnavailable`
  and `maxSurge`; `Recreate` kills old Pods first (for volumes that can only
  mount once). Setting a new `image` (or any template field) starts a rollout.
- **Rollouts**: `kubectl rollout status|history|undo|pause|resume`. Use
  `kubectl set image`, add a `change-cause` annotation, and roll back to a
  known-good revision with `kubectl rollout undo --to-revision`.
- **HorizontalPodAutoscaler**: scales a Deployment on observed metrics
  (CPU is built in; custom metrics need an adapter). `kubectl get hpa`, and
  watch `kubectl get deploy -w` when a load test spikes CPU.
- **Service & Endpoints**: a Service selects Pods by label and load-balances
  the ClusterIP across their Endpoints. A headless Service (`clusterIP:
  None`) gives you the Pod IPs for DNS-based discovery (StatefulSet clients).
  A broken selector = empty Endpoints = "connection refused" mystery.
- **Ingress**: a namespaced API object that routes HTTP(S) from one entrypoint
  to Services by host and path, subject to `ingressClassName` and the actual
  controller you installed (nginx, Traefik). It does nothing by itself — no
  controller, no routing.
- **DNS**: pods resolve `svc.namespace.svc.cluster.local`. Within the same
  namespace the short name works. Pods get `pod-ip.namespace.pod.cluster.local`
  too. A name that won't resolve is a Service/selector problem, not a DNS one.
- **Volumes**: `emptyDir` is a per-Pod scratch disk (wiped on Pod restart),
  `hostPath` mounts a node directory (don't for app data), and
  `persistentVolumeClaim` mounts a PVC — the durable, recommended path. Access
  modes (`RWO`, `ROX`, `RWX`) constrain who can mount what.
- **Resource requests/limits**: requests book capacity and gate scheduling;
  limits cap CPU and memory (memory limits trigger OOMKill). CKAD tasks
  routinely ask you to set both — undersized Pods fail probes for the wrong
  reason.

## Hands-on exercises

All exercises assume a working cluster and namespace of your own.

### Exercise 1 — Multi-container Pod: init + sidecar

- Task: build a Pod with an init container that writes to a shared `emptyDir`,
  and a sidecar that serves it while the main container runs.
- Expected outcome: the init container exits 0 before the main containers
  start; both containers in the Pod run; the file written by init is visible
  to the sidecar.

```sh
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: multi
spec:
  initContainers:
    - name: seed
      image: busybox:1.36
      command: ["sh", "-c", "echo ready > /shared/ready"]
      volumeMounts:
        - name: shared
          mountPath: /shared
  containers:
    - name: app
      image: nginx:stable-alpine
      volumeMounts:
        - name: shared
          mountPath: /shared
    - name: sidecar
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
      volumeMounts:
        - name: shared
          mountPath: /shared
  volumes:
    - name: shared
      emptyDir: {}
EOF
```

- Verification (init has completed; both containers show `Running`; file
  exists from inside the sidecar):

```sh
kubectl get pod multi
kubectl get pod multi -o jsonpath='{.status.initContainerStatuses[0].state.terminated.exitCode}{"\n"}'
kubectl exec multi -c sidecar -- cat /shared/ready
```

### Exercise 2 — ConfigMaps and Secrets

- Task: create a ConfigMap with a URL and a Secret with credentials, mount
  both as files and as environment, and read them from inside the Pod.
- Expected outcome: the Pod sees `APP_URL`, `APP_USER`, and `APP_PASS` as env
  vars, and `/config/url` plus `/secrets/pass` as files.

```sh
kubectl create configmap app-config --from-literal=url=https://api.example.com
kubectl create secret generic app-secret --from-literal=user=admin --from-literal=pass=sup3rs3cret
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: configured
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "env | grep APP; cat /config/url; cat /secrets/pass; sleep 3600"]
      env:
        - name: APP_URL
          valueFrom:
            configMapKeyRef: { name: app-config, key: url }
        - name: APP_USER
          valueFrom:
            secretKeyRef: { name: app-secret, key: user }
      envFrom:
        - secretRef: { name: app-secret }
      volumeMounts:
        - name: cfg
          mountPath: /config
        - name: sec
          mountPath: /secrets
  volumes:
    - name: cfg
      configMap: { name: app-config }
    - name: sec
      secret: { secretName: app-secret }
EOF
```

- Verification (values visible; Secrets stored base64 in the API):

```sh
kubectl logs configured
kubectl get secret app-secret -o jsonpath='{.data.pass}' | base64 -d
```

### Exercise 3 — Probes and self-healing

- Task: deploy a Pod whose readiness probe checks `/healthz`, then break the
  endpoint and watch readiness flip while liveness keeps it alive; finally
  break liveness and watch the container restart.
- Expected outcome: while the endpoint returns 200 the Pod is `Ready`; when it
  returns 500 the Pod is `Running` but not `Ready`; a liveness failure
  increments `RESTARTS` as kubelet kills and reschedules the container.

```sh
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: probed
spec:
  containers:
    - name: app
      image: busybox:1.36
      command:
        - sh
        - -c
        - |
          i=0
          while true; do
            i=$((i+1))
            echo "HTTP/1.1 200 OK" | nc -l -p 8080 -q 1 >/dev/null
            sleep 1
          done
      ports: [{ containerPort: 8080 }]
      readinessProbe:
        httpGet: { path: /, port: 8080 }
        initialDelaySeconds: 2
        periodSeconds: 2
EOF
kubectl wait --for=condition=Ready pod/probed --timeout=60s
```

- Verification (`Ready` true, then flip by replacing the probe path with one
  that 404s and re-watching):

```sh
kubectl get pod probed -o wide
kubectl exec probed -- sh -c 'wget -qO- http://localhost:8080/' || true
kubectl describe pod probed | grep -i probe
```

### Exercise 4 — Rollouts, pause, and rollback

- Task: deploy `app` at image v1, `set image` to v2 with a `change-cause`,
  pause the rollout mid-way, resume it, then roll back to revision 1.
- Expected outcome: `kubectl rollout history` shows two revisions with
  change-cause annotations; `undo` restores v1 and `rollout status` confirms
  the old ReplicaSet scaling down.

```sh
kubectl create deployment app --image=nginx:1.27 --replicas=3
kubectl set image deployment/app nginx=nginx:1.27 --record
kubectl annotate deployment/app kubernetes.io/change-cause="bump to stable"
kubectl rollout pause deployment/app
kubectl set image deployment/app nginx=nginx:stable-alpine
kubectl rollout status deployment/app   # stays paused; no new pods
kubectl rollout resume deployment/app
kubectl rollout status deployment/app
kubectl rollout undo deployment/app
kubectl rollout status deployment/app
```

- Verification:

```sh
kubectl rollout history deployment/app
kubectl get deployments,replicasets,pods -l app=app
```

### Exercise 5 — Services, Ingress, and PVC-backed storage

- Task: expose `app` through a ClusterIP Service, add an Ingress route on host
  `app.example.com`, and attach a PVC that survives Pod deletion.
- Expected outcome: `kubectl get svc` shows a ClusterIP with matching
  Endpoints; the Ingress object lists the host and service; the PVC binds and
  the data survives a Pod recreation.

```sh
kubectl expose deployment app --name=app-svc --port=80 --target-port=80
kubectl apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ing
spec:
  ingressClassName: nginx
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app-svc
                port: { number: 80 }
EOF
kubectl create namespace data
kubectl -n data apply -f - <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-data
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 1Gi
EOF
kubectl -n data apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: stateful
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "echo persist > /data/file; sleep 3600"]
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: app-data
EOF
```

- Verification:

```sh
kubectl get svc,endpoints,ingress
kubectl get pvc -n data
kubectl -n data exec stateful -- cat /data/file
kubectl -n data exec stateful -- nslookup app-svc.default.svc.cluster.local 2>/dev/null || true
```

## Test yourself

When you can do Exercises 1–5 without the book, sit simulator attempts on
`banks/ckad`:

- **First pass**: **Training**, `focus_domain = application-design-build`.
- **Second pass**: **Training**, `focus_domain = configuration-security`.
- **Third pass**: **Mastery**, `focus_domain = application-deployment` —
  rollouts and probes are where CKAD timing goes wrong.
- **Final pass**: full-bank **Mastery**, timed to the bank's
  `duration_minutes`.

If `services-networking` shows up weak, redo Exercise 5's service/ingress
half; if `observability-maintenance` is weak, redo Exercise 3.

## See also

- CKAD certification page on linuxfoundation.org (referenced by name).
- [Module 4 — Security](04-security.md) — next: the CKS and KCSA tracks.
