# Security

## Threat model

This platform is built for **one learner on a private lab**: it has **no
authentication** anywhere. Anyone who can reach the facilitator port can
create attempts, read question banks, and (through the conductor) run commands
against your cluster. Treat it as a single-user tool.

## What is exposed by default

| Port | Service | Default bind |
|---|---|---|
| 8900 | facilitator (UI/API) | 127.0.0.1 (loopback only) |
| 9001 | conductor (internal) | internal network only |
| 5100 | registry (internal) | loopback only |

Default bindings mean only processes on the same host can reach the UI.

## `ga expose` — the deliberate tradeoff

`./ga expose` (or `GA_BIND=0.0.0.0`) rebinds the facilitator to all
interfaces so you can practice from another machine on your LAN. This is an
**explicit opt-in**, not a default:

- No authentication stands in for a login.
- Anyone on the LAN who finds port 8900 can use the platform and trigger
  grading commands.
- Never port-forward 8900 (or the registry 5100) on your router to the public
  Internet.
- Prefer a VPN or SSH tunnel (`ssh -L 8900:127.0.0.1:8900 user@host`) over a
  bare expose when you are not on a trusted network.

## The conductor runs commands

Hands-on grading executes real shell/`oc` commands against the cluster
configured via `GA_CLUSTER`. Consequence:

- Run the platform on nodes you are willing to have touched by whatever the
  learner types in the exam desktop.
- Point it at a **practice cluster only** (CRC/OKD/lab), never production.
- `GA_CMD_TIMEOUT` caps each check; the conductor uses `BatchMode=yes` for SSH
  so it never prompts.

## Secrets

- No credentials are stored by the platform.
- Your Red Hat pull secret (if used with `cluster/crc.sh`) goes to the CRC
  bundle location, not into this project.
- The kubeconfig mounted into the conductor (`~/.kube/config`) is read-only;
  nothing writes to it.

## Reporting issues

This is a personal learning project. If you find a vulnerability in the
engine or docs, open an issue on the repository rather than emailing — and
never attach kubeconfigs, pull secrets, or cluster admin credentials.
