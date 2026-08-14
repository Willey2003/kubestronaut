# The `ga` CLI

```bash
./ga <command>
```

| Command | What it does |
|---|---|
| `doctor` | Preflight: python, docker, compose, oc, RAM |
| `validate` | Validate every bank in `banks/` (format + rules) |
| `build` | Build the facilitator + conductor images |
| `up` | Start the platform (`docker compose up -d --build`) |
| `down` | Stop the platform (attempt state preserved) |
| `logs [svc]` | Follow platform logs (facilitator/conductor/registry) |
| `expose` | Rebind facilitator to `0.0.0.0` for LAN use (opt-in; no auth) |
| `status` | List banks and recent attempts with scores |
| `exam <bank>` | Headless: create a Mastery attempt and print its id |

## Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `GA_BIND` | `127.0.0.1` | Host bind address for published ports (use `0.0.0.0` to expose) |
| `GA_CLUSTER` | `local` | Conductor cluster backend: `none`, `local`, `remote://user@host` |
| `GA_CMD_TIMEOUT` | `30` | Seconds per grading check command |
| `KUBECONFIG_DIR` | `~/.kube` | Directory mounted into the conductor for cluster access |

## Headless usage

```bash
./ga exam ex280-admin --mode training
# -> prints attempt id; open http://localhost:8900/exam.html?attempt=<id>
```

## Single-bank validation

```bash
python3 -m engine.validator banks/ex288-developer
```
