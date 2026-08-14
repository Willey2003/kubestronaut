# Module 4 — Security

Module 4 is the **CKS** and **KCSA** track: hardening the cluster, the
containers, and the supply chain, and understanding the security model end to
end. CKS is hands-on — you will write RBAC, NetworkPolicies, and
`securityContext`s against a real cluster. KCSA is the associate-level theory:
threat models, frameworks, and compliance. This module covers both.

## Learning objectives

1. Harden the cluster surface: TLS everywhere, restricted kubelet access,
   ServiceAccount token handling, and Pod Security admission.
2. Enforce least privilege with RBAC and verify it with `kubectl auth can-i`.
3. Segment traffic with default-deny NetworkPolicies that allow only what is
   required.
4. Harden containers: non-root, read-only root filesystem, dropped
   capabilities, and seccomp/AppArmor profiles.
5. Secure the supply chain: pin image digests, scan images, sign artifacts,
   and gate admission with an ImagePolicyWebhook or policy engine.
6. Apply runtime security: audit logging, threat detection (Falco), and
   secrets hygiene; and map all of it to a threat model and compliance
   frameworks (KCSA).

## Key concepts

- **Threat model**: enumerate who could attack what. KCSA expects you to
  reason about the four planes — data, application, management, and
  infrastructure — and the vectors on each (compromised image, stolen
  ServiceAccount token, misconfigured RBAC, open dashboard).
- **RBAC aggregation**: `ClusterRole`s can aggregate with
  `kubernetes.io/aggregate-to-*` annotations. Prefer granting the built-in
  `view`/`edit`/`admin` role families and building small custom roles over
  ever creating `cluster-admin`.
- **ServiceAccount hardening**: Pods inherit the default SA's token unless you
  set `automountServiceAccountToken: false`. Only workloads that genuinely
  call the API need a token; for the rest, opt out — a leaked token is the
  classic pivot into the cluster.
- **Pod Security Standards**: three tiers — `privileged`, `baseline`,
  `restricted`. The `PodSecurity` admission controller enforces a tier per
  namespace via labels (`pod-security.kubernetes.io/enforce=restricted`); a
  Pod that violates the tier is rejected. This replaced PodSecurityPolicies
  (removed in 1.25).
- **securityContext**: per-Pod or per-container controls —
  `runAsNonRoot`, `runAsUser`, `allowPrivilegeEscalation: false`, `seccompProfile:
  {type: RuntimeDefault}`, `capabilities: {drop: [ALL]}`,
  `readOnlyRootFilesystem: true`. A container that violates restricted is the
  first thing CKS tasks check.
- **Seccomp and AppArmor**: seccomp filters syscalls
  (`RuntimeDefault` is the practical baseline); AppArmor constrains programs
  by profile (on systems that ship it). Together with dropped capabilities
  they shrink the kernel attack surface a container can reach.
- **NetworkPolicy**: a namespace-scoped firewall on Pod labels. `policyTypes:
  [Ingress, Egress]` plus empty `podSelector` creates a default deny; then
  allow rules by pod and namespace selector, with `ports`. It's enforced by
  the CNI (Calico, Cilium) — a cluster without a policy-capable CNI ignores
  them silently.
- **Image hygiene**: prefer `imagePullPolicy: IfNotPresent`/`Always` with an
  explicit digest (`image: app@sha256:...`), use minimal/distroless bases,
  scan with `trivy`/`grype`, and never run as root in the image
  (`USER` in the Dockerfile, `runAsNonRoot` at runtime).
- **Signing and provenance**: sign images with `cosign` (sigstore) and store
  attestations; the `ImagePolicyWebhook` admission controller can reject
  images that fail signature verification, and in-toto/SLSA provenance
  documents what built the artifact and from what.
- **Admission control**: admission controllers run after authN/authZ, before
  the object is persisted. `ImagePolicyWebhook` and OPA Gatekeeper/Kyverno
  policies are where cluster-wide security rules actually get enforced.
- **Audit logging**: the apiserver's `--audit-policy-file` defines which
  verbs/levels to record (Metadata/Request/RequestResponse), and
  `--audit-log-path` where. Audit logs are the forensic source for CKS
  runtime questions and for detecting `kubectl exec` into a pod.
- **Runtime detection**: Falco watches syscalls at the kernel level
  (a privileged DaemonSet) and alerts on suspicious behaviour — shell in a
  container, privilege escalation, unexpected file writes. `kube-bench` runs
  CIS benchmarks against nodes and the control plane.
- **Secrets hygiene**: Secrets are base64, not encrypted, in etcd unless
  you enable encryption at rest (`--encryption-provider-config` with aescbc/
  aesgcm). Rotate via `SealedSecrets`/external providers (Vault) in production
  rather than committing them to git.

## Hands-on exercises

CKS exercises need a kubeadm-based cluster (kind works; the apiserver
`PodSecurity` and audit parts are best on a real kubeadm node). Create a
throwaway namespace `sec` for everything below.

### Exercise 1 — Enforce Pod Security restricted on a namespace

- Task: label namespace `sec` to enforce the `restricted` Pod Security
  Standard, then try to run a privileged Pod and a compliant one.
- Expected outcome: the privileged Pod is rejected with a
  `Forbidden: violates PodSecurity "restricted"` error; the compliant Pod runs.

```sh
kubectl create namespace sec
kubectl label namespace sec pod-security.kubernetes.io/enforce=restricted
kubectl run bad --image=nginx:stable-alpine --restart=Never -n sec 2>&1 | head -1
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: good
  namespace: sec
spec:
  securityContext:
    runAsNonRoot: true
    seccompProfile: { type: RuntimeDefault }
  containers:
    - name: nginx
      image: nginx:stable-alpine
      securityContext:
        allowPrivilegeEscalation: false
        capabilities: { drop: ["ALL"] }
EOF
```

- Verification:

```sh
kubectl get pod good -n sec
kubectl auth can-i create pods -n sec --as=system:serviceaccount:sec:default
```

### Exercise 2 — Least-privilege RBAC with can-i proof

- Task: create ServiceAccount `pods-only` that may only get/list pods in `sec`,
  and prove every other verb is denied.
- Expected outcome: `get` and `list` return `yes`; `delete`, `create`, and
  anything in another namespace return `no`.

```sh
kubectl create serviceaccount pods-only -n sec
kubectl -n sec apply -f - <<'EOF'
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: sec
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list"]
EOF
kubectl -n sec apply -f - <<'EOF'
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pods-only-reader
  namespace: sec
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: pod-reader
subjects:
  - kind: ServiceAccount
    name: pods-only
    namespace: sec
EOF
```

- Verification (yes / no / no / no in order):

```sh
kubectl auth can-i get pods -n sec --as=system:serviceaccount:sec:pods-only
kubectl auth can-i delete pods -n sec --as=system:serviceaccount:sec:pods-only
kubectl auth can-i create pods -n sec --as=system:serviceaccount:sec:pods-only
kubectl auth can-i get pods -n default --as=system:serviceaccount:sec:pods-only
```

### Exercise 3 — Default-deny NetworkPolicy with a precise allow

- Task: deploy `web` (nginx) and `client` (busybox) Pods in `sec`, then create
  a NetworkPolicy that denies all ingress to `web` except from `client`.
- Expected outcome: with no policy everything reaches `web`; after the policy,
  `client` still curls `web` but `curl` from a third, unselected Pod times out.

```sh
kubectl -n sec run web --image=nginx:stable-alpine --labels=app=web
kubectl -n sec run client --image=busybox:1.36 --labels=app=client -- sh -c "sleep 3600"
kubectl -n sec run stranger --image=busybox:1.36 -- sh -c "sleep 3600"
kubectl -n sec apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-web-ingress
  namespace: sec
spec:
  podSelector:
    matchLabels:
      app: web
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: client
EOF
```

- Verification (`200` from client; no response from stranger):

```sh
kubectl -n sec exec client -- wget -qO- --timeout=5 http://web/ | head -1
kubectl -n sec exec stranger -- wget -qO- --timeout=5 http://web/ | head -1
kubectl -n sec get networkpolicies
```

### Exercise 4 — Container runtime hardening

- Task: run the same nginx image hardened — non-root, read-only root
  filesystem, all capabilities dropped, `RuntimeDefault` seccomp — and prove
  the restrictions bite.
- Expected outcome: the Pod runs; writing to `/` fails
  (`read-only file system`); the effective user is non-root.

```sh
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: hardened
  namespace: sec
spec:
  securityContext:
    seccompProfile: { type: RuntimeDefault }
  containers:
    - name: nginx
      image: nginx:stable-alpine
      securityContext:
        runAsNonRoot: true
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: ["ALL"]
EOF
```

- Verification:

```sh
kubectl -n sec get pod hardened
kubectl -n sec exec hardened -- sh -c 'touch /x' 2>&1 | tail -1
kubectl -n sec exec hardened -- id
```

### Exercise 5 — Supply chain and runtime drills

- Task: pin an image by digest with `imagePullPolicy: IfNotPresent`, scan it
  for vulnerabilities, and inspect the apiserver's audit configuration.
- Expected outcome: the Pod references `nginx@sha256:...`; the scan reports
  (or the tool is absent, in which case note it as a gap); you can state
  whether the apiserver writes audit logs and where.

```sh
kubectl run pinned --image=nginx:stable-alpine --restart=Never -n sec \
  --overrides='{"spec":{"containers":[{"name":"pinned","image":"nginx:stable-alpine@sha256:$(skopeo inspect docker://nginx:stable-alpine --format {{.Digest}} 2>/dev/null || echo not-available)","imagePullPolicy":"IfNotPresent"}]}}' 2>/dev/null || echo "digest-pinning needs skopeo or a registry push"
trivy image --severity HIGH,CRITICAL --exit-code 1 nginx:stable-alpine 2>/dev/null || echo "install trivy: https://aquasecurity.github.io/trivy/"
kubectl -n kube-system get pod kube-apiserver-$(kubectl get nodes -o name | cut -d/ -f2) -o jsonpath='{.spec.containers[0].command}' | tr ' ' '\n' | grep -E 'audit-(log-path|policy-file)' || echo "no audit flags configured"
```

- Verification:

```sh
kubectl -n sec get pod pinned -o jsonpath='{.spec.containers[0].imagePullPolicy}{"\n"}'
kubectl -n sec get pod pinned -o jsonpath='{.status.containerStatuses[0].image}{"\n"}'
```

## Test yourself

When you can do Exercises 1–5 without the book, sit simulator attempts:

- **CKS hands-on**: `banks/cks` — first **Training**, `focus_domain =
  cluster-hardening`; then **Mastery**, `focus_domain = runtime-security`;
  then **Mastery**, `focus_domain = microservice-vulnerabilities`.
- **KCSA theory**: `banks/kcsa` — **Training**, `focus_domain =
  cluster-security`; then **Training**, `focus_domain = threat-model`; then
  **Mastery**, `focus_domain = compliance-frameworks`.
- **Final**: full-bank **Mastery** on `banks/cks`, timed to its
  `duration_minutes`, then full-bank **Mastery** on `banks/kcsa`.

Security scores are the most sensitive to skipping exercises — NetworkPolicy
and RBAC behaviour can't be learned from a slide. Re-run Exercise 3 before any
`runtime-security` retake.

## See also

- CKS and KCSA certification pages on linuxfoundation.org (referenced by
  name).
- [Module 5 — Monitoring](05-monitoring.md) — next: the CPNA
  (Prometheus + Grafana) track.
