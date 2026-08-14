# Roadmap

Current: **v0.1 platform + content** (this release). Everything below is
planned; nothing in this file is a promise.

## v0.1 — done in this repo

- [x] From-scratch engine: bank loader with stratified draws, validator,
      conductor grader (knowledge + behaviour checks), facilitator UI/API,
      attempt persistence, `ga` CLI
- [x] Docker deployment: facilitator, conductor (with oc/kubectl), registry
- [x] Banks: EX280 admin (20q), EX288 developer (20q), Knowledge (30q)
- [x] Curriculum: 8-week guided path for both tracks, 12 modules
- [x] Labs: EX280-01, EX288-01, EX288-02 with verification checks
- [x] Cluster tooling: CRC + OKD helpers, preflight

## v0.2 — exam realism

- [ ] Configurable per-question point values and partial-credit rules in the
      bank spec
- [ ] Multiple-answer knowledge questions and ordering/matching questions
- [ ] Timer pausing/resume in Mastery, pause-on-tab-hidden in Exam
- [ ] "Weakest domains first" study plan generator from attempt history
- [ ] Per-question feedback in Exam mode after submission (like the real
      score screens)

## v0.3 — richer hands-on grading

- [ ] Idempotent task **setup** steps that restore a clean starting state
      before each hands-on attempt (cleanup + rebuild lab objects)
- [ ] Cluster backend that grades through the OpenShift REST API instead of a
      local shell (remove the privileged-command surface)
- [ ] Snapshot/rollback of CRC between attempts (`crc` snapshot support) so
      every attempt starts identical
- [ ] Image-build questions that actually push to the platform registry

## v0.4 — learning platform

- [ ] Progress tracking: per-domain mastery scores over time, XP, streaks
- [ ] Spaced-repetition drills fed by weak domains
- [ ] Step-by-step guided solutions (walkthrough mode) for hands-on tasks
- [ ] Import/export of attempt history (JSON) for long-term tracking

## Later

- [ ] More banks: EX374 (Ansible), RHCSA-style knowledge, KCSA/KCNA cross-ref
- [ ] Multi-user mode with simple sign-in (password auth) behind a reverse
      proxy (Caddy/Traefik)
- [ ] Web-based workspace instead of relying on the host terminal
- [ ] ARM64 images (Apple Silicon / Raspberry Pi labs)
