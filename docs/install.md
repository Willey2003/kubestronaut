# Installation

Golden Astronaut 2026 runs as a small Docker stack (facilitator UI/API,
conductor grader, registry) plus your own OpenShift cluster for practice.

## Requirements

- Docker Engine 20.10+ with Compose v2
- Python 3.10+ (host tooling only — the engine runs in containers)
- ~1 GB free RAM for the platform stack; ~9 GB more if you run OpenShift Local
  on the same host
- `oc` client on the host that talks to your cluster (see
  [docs/cluster-setup.md](cluster-setup.md))

## 1. Get the project

```bash
git clone <your-repo-url> golden-astronaut-2026
cd golden-astronaut-2026
```

## 2. Preflight

```bash
./ga doctor        # checks python, docker, compose, oc, RAM
./cluster/preflight.sh   # checks the host can run an OpenShift cluster
```

## 3. Start the platform

```bash
./ga build         # build facilitator + conductor images
./ga up            # start facilitator (:8900), conductor, registry
```

Open <http://localhost:8900> in your browser. The pages list the three banks
(EX280 admin, EX288 developer, Knowledge).

### Reach it from another machine on your LAN

```bash
./ga expose
```

This rebinds the facilitator to `0.0.0.0`. The platform has **no
authentication** — see [docs/security.md](security.md) before doing this.

## 4. Point the conductor at your cluster

Hands-on questions need `oc` access to a cluster. On this host that means a
kubeconfig in `~/.kube/config` (see [docs/cluster-setup.md](cluster-setup.md)).
The conductor container mounts `~/.kube` read-only. If your cluster is on a
different machine, set `GA_CLUSTER=remote://user@host` in your environment
before `./ga up`.

## 5. Sit an exam

- **Training** — no clock, solutions shown, not scored (learn).
- **Mastery** — timed, domain-focussed, scored (drill).
- **Exam** — full countdown, scored like the real thing (rehearse).

Every attempt is saved under `state/` and shown on the home page with score
and weakest domains.

## Uninstall / stop

```bash
./ga down          # stops containers; state/ is preserved
docker compose down -v   # also delete state + registry volumes
```
