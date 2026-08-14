# Architecture

Golden Astronaut 2026 is an original, self-contained learning and exam
simulation platform. It is designed to be run on one host (a local VM, a
workstation, or a lab server) and to drive practice against a **real
OpenShift cluster**.

## Principles

- **From scratch.** No code copied from other simulators. Owned by you.
- **Zero runtime language dependencies.** The engine is pure Python 3 stdlib;
  it needs no pip packages.
- **Behaviour grading.** Hands-on tasks are scored by executing real commands
  against the cluster (`oc get`, `oc apply`, policy probes), never by string
  matching YAML.
- **Separation of concerns.** The facilitator (presentation/sessions), the
  conductor (grading), and the cluster (the world being graded) are separate
  processes so each can scale, be secured, or be replaced independently.

## Components

```
                          +------------------------------------------+
                          |                Browser (you)               |
                          +---------------------+--------------------+
                                                | HTTP / HTTPS
                                                v
   +--------------------------------------+     |
   |  FACILITATOR  (engine/facilitator.py)|<----+
   |  - web UI + JSON API                 |
   |  - sessions, modes, timers           |
   |  - question draws (stratified)       |
   |  - writes attempts to state/         |
   +------------+-------------------------+
                | reads banks + spawns grading jobs
                v
   +------------+-------------------------+
   |  CONDUCTOR  (engine/conductor.py)    |
   |  - validates attempts                |
   |  - grades MCQ + knowledge            |
   |  - runs behaviour checks via         |
   |    oc/kubectl against the cluster    |
   |  - emits verdicts + solutions        |
   +------------+-------------------------+
                | oc / kubectl / ssh
                v
   +------------+-------------------------+
   |  OPENSHIFT CLUSTER (cluster/)        |
   |  - OpenShift Local (CRC) or OKD      |
   |  - candidate workspaces (labs)       |
   +--------------------------------------+
```

### Facilitator
- HTTP server (stdlib `http.server`), serves the UI and a small JSON API.
- Owns the concept of an **attempt**: bank, mode, drawn questions, timer,
  answers, status.
- Modes: `training` (no clock, solutions visible, ungraded),
  `mastery` (clock, domain-scoped draws, graded, kept), `exam`
  (full countdown, graded, kept).
- Persists attempts to `state/` as JSON so `down`/`up` resumes them.

### Conductor
- Consumes an attempt, scores it, returns per-question verdicts, a percentage,
  pass/fail against the bank threshold, and the weakest domains.
- For multiple-choice/knowledge questions: exact-match scoring with a
  documented weighting rule.
- For hands-on questions: runs the task's `checks` — a sequence of commands
  (default shell or `oc`), each with an expected result, via a pluggable
  **cluster backend** (`local` uses a local `oc`/`kubectl`; `remote` uses ssh;
  `none` marks questions ungraded in Training).

### Cluster backends (engine/cluster_backend.py)
- `local` — run `oc`/`kubectl` on the host. Simplest; used when the simulator
  runs on the same machine as OpenShift Local.
- `remote` — run commands over SSH (`oc` on the cluster host). For when the
  cluster lives on another VM.
- `none` — no cluster; only knowledge questions are graded. Used by `ga doctor`
  and Training without a cluster.

### Data model
- **Bank** — a directory `banks/<bank>/` with `exam.yaml` (metadata, draw
  config, pass threshold, curriculum weights) and one YAML file per question
  (`qNN.yaml`). See [docs/bank-spec.md](bank-spec.md).
- **Attempt** — JSON in `state/<bank>-<id>.json`.
- **Curriculum** — Markdown learning paths under `curriculum/`.

## Ports (defaults)

| Port | Service | Bind | Purpose |
|---|---|---|---|
| 8900 | facilitator UI/API | 127.0.0.1 | pick an exam, sit it |
| 9001 | conductor API | 127.0.0.1 | internal grading |
| 5100 | registry | 127.0.0.1 | image push for build tasks |
| 6080/6081 | desktop (noVNC) | 127.0.0.1 | optional GUI workspace |

`ga expose` rebinds the facilitator (+ optional desktop) to `0.0.0.0` for LAN
use — see [docs/security.md](security.md) for the deliberate-tradeoff section.

## Security boundaries

- The platform has **no authentication** (single user / private lab). Bind to
  loopback by default; `ga expose` is an explicit opt-in.
- Hands-on grading runs shell commands against your cluster: run it on nodes
  you are willing to have a user's commands touch.
- Never forward 8900 to the public Internet. See [docs/security.md](security.md).
