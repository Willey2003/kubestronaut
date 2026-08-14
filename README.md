# Kubestronaut 2026

The **Linux Foundation / CNCF** certification learning and exam-simulation
platform — every listed 2026 certification in one project, with original
practice banks, a guided curriculum, and behaviour-graded hands-on tasks.

> Certifications covered (2026):
> **CKA** · **CKAD** · **CKS** · **KCNA** · **KCSA** · **CPNA**
> plus the **Prometheus** and **Grafana** monitoring skill tracks.

This project is an original, from-scratch codebase (no code reused from other
simulators). Question banks are **original practice questions written to the
published exam objectives** — they are not reproductions of real exam dumps.

## The stack

- **Engine** — facilitator (UI/API), conductor (grader), bank loader +
  validator, `ga` CLI. Pure Python stdlib.
- **Exams** — one bank per certification, Training / Mastery / Exam modes,
  stratified draws, pass thresholds, weakest-domain reporting.
- **Curriculum** — a guided 8-week path with one module per cert.
- **Labs** — hands-on exercises with verification commands against a real
  Kubernetes cluster.

## Quick start

```bash
./ga doctor        # preflight
./ga up            # start platform (default http://127.0.0.1:8901)
```

Open <http://127.0.0.1:8901> (or the LAN address after `./ga expose`).

## Certification banks

| Bank | Certification | Engine |
|---|---|---|
| `cka` | Certified Kubernetes Administrator | hands-on |
| `ckad` | Certified Kubernetes Application Developer | hands-on |
| `cks` | Certified Kubernetes Security Specialist | hands-on |
| `kcna` | Kubernetes and Cloud Native Associate | knowledge |
| `kcsa` | Kubernetes and Cloud Native Security Associate | mixed |
| `cpna` | Cloud Native / Prometheus monitoring (Prometheus + Grafana) | mixed |

See `docs/` for architecture, bank spec, install, and security.

## License

Apache-2.0. Independent project — not affiliated with the Linux Foundation or
CNCF. Certification names are trademarks of their owners.
