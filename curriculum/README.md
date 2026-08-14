# Kubestronaut 2026 — Learning Curriculum

This directory is the guided study path for the **Kubestronaut 2026** platform.
It is not a topic dump: it tells you **what** to study, **in what order**, and
**when** to sit which practice attempt against the simulator and your real
cluster. Work the modules top to bottom — later modules assume the skills of
earlier ones.

| Module | Title | Target certification | Bank | Engine |
|---|---|---|---|---|
| [01](01-kubernetes-foundations.md) | Kubernetes foundations | KCNA | `banks/kcna` | knowledge |
| [02](02-administration.md) | Administration | CKA | `banks/cka` | hands-on |
| [03](03-application-development.md) | Application development | CKAD | `banks/ckad` | hands-on |
| [04](04-security.md) | Security | CKS · KCSA | `banks/cks`, `banks/kcsa` | hands-on · mixed |
| [05](05-monitoring.md) | Monitoring (Prometheus + Grafana) | CPNA | `banks/cpna` | mixed |

## How to use this path

1. **Read the module.** Start with the learning objectives, then the key
   concepts. Concepts are ordered so that each one builds on the last.
2. **Do the exercises on a real cluster.** Every exercise has a concrete task,
   an expected outcome, and the exact `kubectl` command to verify it. Do not
   skip verification — if the check fails, the cluster state is not what you
   think it is.
3. **Finish each module with its "test yourself" block.** Sit a simulator
   attempt on the module's bank, narrowed to that module's `focus_domain`.
   Start in **Training** mode (solutions shown), then redo it in **Mastery**
   mode (timed, no hints).
4. **Escalate to Exam mode only after several clean Mastery passes.** The
   rhythm is *Training → Mastery → Exam*. Jumping straight to Exam wastes the
   most informative mode you have.
5. **Let the attempt report drive review.** The report ranks your domains
   weakest-first. Re-run the matching exercises, then drill that domain with a
   focused Mastery attempt.
6. **Repeat until 0.70.** The banks' `pass_threshold` is 0.70. Sit full-length
   Exam attempts until you score at or above it on three consecutive attempts
   per bank.

## Prerequisite skills

You should be comfortable with the following **before** starting Week 1:

- **Linux command line** — navigating the filesystem, running commands,
  redirecting and piping output, editing files with `vim`/`nano`.
- **`kubectl` basics** — you have run `kubectl get nodes` at least once and
  understand contexts and `-n` namespace flags.
- **YAML** — indentation, mappings, lists. Almost every exercise is writing or
  reading YAML.
- **Container basics** — what an image is, images vs. containers, registries
  and tags, and a rough idea of what a `Dockerfile` does.
- **Networking fundamentals** — IP addresses, ports, TCP, HTTP, and DNS at a
  conceptual level.

No Kubernetes administration experience is required to start Module 1, but the
faster you can type a `kubectl` command the further each module's exercises
take you.

## Tooling setup

Install these before your first attempt. Run `./ga doctor` in the repo root
for a preflight check.

- **`kubectl` CLI** — the Kubernetes client. Install a version within ±1 of
  your cluster's server version (`kubectl version --client` vs `kubectl
  version` after connecting). On OpenShift clusters `oc` is a drop-in
  superset; the curriculum uses `kubectl`.
- **A cluster** — any one of these works; the grader just needs `kubectl` to
  reach it with a kubeconfig in `~/.kube/config`:
  - **kind** — fastest to stand up, ideal for Modules 1–3 and most of 4.
  - **k3s** — single binary, good for low-RAM laptops; note its default
    embedded kubelet options differ slightly from kubeadm clusters.
  - **OpenShift Local (CRC)** — the closest thing to a production control
    plane; heaviest (4 vCPU, ~9 GiB RAM).
  - For security exercises (Module 4) a kubeadm-based cluster is recommended,
    because the exercises touch `kube-apiserver` static-pod flags.
- **Python 3 + Docker** — the platform stack (`./ga doctor`, `./ga up`).
- **Optional but useful**: `helm`, `jq`, `trivy`, and `cosign` for Modules 4–5.

Verify the plumbing, then start the platform:

```bash
./ga doctor
./ga up                    # http://127.0.0.1:8901
kubectl cluster-info
kubectl get nodes
```

## Simulator modes

Every bank can be attempted in three modes. They exist to be used **in that
order**:

| Mode | Timer | Answer reveal | Use it for |
|---|---|---|---|
| **Training** | Off | Solutions + explanations shown immediately | Learning each domain right after a module |
| **Mastery** | On | Hidden until graded | Practicing under time pressure without hints |
| **Exam** | On | Hidden until graded | Full dress rehearsal at real exam duration |

Attempts are drawn stratified by **domain**. You can restrict a Mastery or
Training attempt to a single domain with `focus_domain` — that is how you
target exactly what a module just taught. The domain names live in each bank's
`exam.yaml` and match the vocabulary below.

## Bank domains (the `focus_domain` vocabulary)

Each bank is stratified into domains. Use these names in the UI's `focus
domain` selector (or `./ga exam <bank> --focus-domain <domain>`):

| Bank | Domains |
|---|---|
| `kcna` | `cloud-native-landscape`, `containers`, `kubernetes-fundamentals`, `application-delivery`, `observability`, `security` |
| `cka` | `cluster-architecture-installation`, `workloads-scheduling`, `services-networking`, `storage`, `troubleshooting`, `cluster-maintenance`, `security-rbac` |
| `ckad` | `application-design-build`, `application-deployment`, `configuration-security`, `observability-maintenance`, `services-networking` |
| `cks` | `cluster-setup-hardening`, `cluster-hardening`, `system-hardening`, `microservice-vulnerabilities`, `supply-chain-security`, `runtime-security` |
| `kcsa` | `cluster-security`, `threat-model`, `platform-infrastructure`, `compliance-frameworks`, `supply-chain`, `runtime-workload-security` |
| `cpna` | `observability-fundamentals`, `metrics-collection`, `promql`, `grafana`, `alerting`, `architecture-slos` |

## Study rhythm

The pattern repeats for every module, and it is the whole point of the
platform:

1. **After a module** → a **Training** attempt, focused on that module's
   domain. Read every explanation, even for questions you answered correctly.
2. **After two modules** → a **Mastery** attempt spanning those domains.
   Time-box it; no hints.
3. **After all five modules** → one full-bank **Training** attempt, then one
   full-bank **Mastery** attempt, on every bank.
4. **The week before the exam** → repeated full-length **Exam** attempts until
   you hit the bank's `pass_threshold` (0.70) on three in a row.

A weak domain on the attempt report is a command to **redo exercises**, not to
re-read the module — the grader checks the same real cluster the exercises
used, so muscle memory is what scores.

## Recommended 10-week schedule

Roughly 10–12 hours per week. Weeks 1–9 introduce one module at a time; week
10 is consolidation. Compress to 8 weeks by merging weeks 5 and 9 into the
following week if you are already comfortable; stretch to 12 by giving
security or monitoring an extra week — the schedule is a floor, not a trap.

| Week | Study | Hands-on | Simulator attempts (mode: bank → domain) |
|---|---|---|---|
| 1 | Module 1 — containers, kubectl, Pods | Ex 1–2 | Training: `kcna` → `containers`, `kubernetes-fundamentals` |
| 2 | Module 1 — Deployments, Services, Namespaces | Ex 3–5 | Training: `kcna` → `application-delivery`; **Mastery**: `kcna` → `kubernetes-fundamentals` |
| 3 | Module 2 — architecture, kubeadm, control plane | Ex 1–2 | Training: `cka` → `cluster-architecture-installation`, `cluster-maintenance` |
| 4 | Module 2 — node management, scheduling, RBAC | Ex 3–4 | Training: `cka` → `workloads-scheduling`, `security-rbac`; **Mastery**: `cka` → `cluster-architecture-installation` |
| 5 | Module 2 — storage, etcd, troubleshooting | Ex 5 | **Mastery**: `cka` → `troubleshooting`, `storage`; first full-bank `cka` Training |
| 6 | Module 3 — multi-container pods, Config, probes | Ex 1–3 | Training: `ckad` → `application-design-build`, `configuration-security` |
| 7 | Module 3 — rollouts, services, PVCs | Ex 4–5 | Training: `ckad` → `application-deployment`; **Mastery**: `ckad` → `services-networking`, full-bank `ckad` Training |
| 8 | Module 4 — CKS hardening, RBAC, NetworkPolicies | Ex 1–3 | Training: `cks` → `cluster-hardening`, `system-hardening`; Training: `kcsa` → `cluster-security` |
| 9 | Module 4 (Ex 4–5) + Module 5 — monitoring | Ex 4–5 + Mon 1–3 | Training: `cks` → `runtime-security`; Training: `cpna` → `promql`, `metrics-collection`; **Mastery**: `kcsa` → `cluster-security` |
| 10 | Consolidation — weak-domain drill + rehearsal | Re-run any failing exercise | Full-bank **Mastery** on weak banks; full-length **Exam** dry runs on every bank until ≥ 0.70 three times in a row |

Adjust the pace: if Module 4's security material is new to you, hold a full
extra week rather than rushing. Pacing beats coverage.

## Reading your attempt report

After every Mastery or Exam attempt the score screen shows per-domain
performance. Treat domains below 70% as a backlog: do one focused Mastery
attempt per weak domain, and re-run the module exercises named in that
domain's row above.

## Relationship to the official certifications

The banks in `banks/` are original practice questions written to the published
exam objectives of the official certifications, which are referenced here **by
name only** — always consult the vendor site for the current objectives, since
they change between exam releases:

- **CKA** — Certified Kubernetes Administrator — the CKA page on
  linuxfoundation.org.
- **CKAD** — Certified Kubernetes Application Developer — the CKAD page on
  linuxfoundation.org.
- **CKS** — Certified Kubernetes Security Specialist — the CKS page on
  linuxfoundation.org.
- **KCNA** — Kubernetes and Cloud Native Associate — the KCNA page on
  linuxfoundation.org.
- **KCSA** — Kubernetes and Cloud Native Security Associate — the KCSA page on
  linuxfoundation.org.
- **CPNA** — the Cloud Native monitoring track (Prometheus + Grafana) — see
  the Prometheus/Grafana certification and training pages on linuxfoundation.org
  and prometheus.io.

Kubestronaut 2026 is an independent simulator, not affiliated with the Linux
Foundation or CNCF. Certification names are trademarks of their owners.

## Contents

- [Module 1 — Kubernetes foundations](01-kubernetes-foundations.md)
- [Module 2 — Administration](02-administration.md)
- [Module 3 — Application development](03-application-development.md)
- [Module 4 — Security](04-security.md)
- [Module 5 — Monitoring (Prometheus + Grafana)](05-monitoring.md)
