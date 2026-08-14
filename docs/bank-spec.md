# Bank specification (v1)

Golden Astronaut 2026 uses its **own** question-bank format. A bank is a
directory; it is validated by `engine/validator.py` (`ga validate`).

## Layout

```
banks/<bank-id>/
  exam.yaml            # bank metadata, draw rules, thresholds
  q001.yaml            # one file per question
  q002.yaml
  ...
```

## exam.yaml

```yaml
id: ex280-admin            # unique bank id (used in CLI: ga exam ex280-admin)
title: EX280 Mock Exam      # display name
engine: mixed               # knowledge | hands-on | mixed
duration_minutes: 180       # real EX280 is 3 hours; adjust for Training
pass_threshold: 0.70        # fraction required to pass
draw_size: 20               # questions drawn per attempt
seed: null                  # fixed RNG seed, or null for random draws
domains:                    # curriculum domains and their draw weights (sum 1.0)
  cluster-configuration: 0.25
  authentication-security: 0.20
  networking: 0.20
  storage: 0.15
  operators: 0.10
  application-lifecycle: 0.10
levels:                     # optional difficulty mix (quick/core/deep)
  quick: 0.4
  core: 0.4
  deep: 0.2
```

## Question file (qNN.yaml)

Two shapes: `kind: knowledge` (multiple choice) and `kind: hands-on`
(cluster task).

### Knowledge

```yaml
kind: knowledge
domain: authentication-security
level: quick
title: Which resource grants a service account permission to list pods?
prompt: |
  A developer needs a ServiceAccount that may list Pods in its namespace.
  Which ClusterRole best matches the requirement?
options:
  A: ClusterRole `system:aggregate-to-edit`
  B: Role `pod-lister` bound to the namespace
  C: ClusterRole `system:basic-user`
  D: Role `deployment-lister`
answer: A
explanation: |
  `system:aggregate-to-edit` aggregates into `edit` ... (full explanation here)
```

Rules:
- `answer` must be one of the `options` keys.
- Exactly one correct answer in v1 (single-select).
- `explanation` is shown in Training and on the score screen.

### Hands-on

```yaml
kind: hands-on
domain: application-lifecycle
level: core
title: Deploy a Route for the greeting service
prompt: |
  A service `greeting` exists in namespace `practice`.
  Create a Route named `greeting-route` that exposes it on the host
  `greeting.example.com` with edge TLS termination.
solution: |
  ```sh
  oc -n practice create route edge greeting-route --service=greeting --hostname=greeting.example.com
  ```
checks:            # behaviour checks, ALL must pass
  - desc: Route exists with the right name and host
    run: oc get route -n practice greeting-route -o jsonpath='{.spec.host}'
    equals: greeting.example.com
  - desc: Service target is correct
    run: oc get route -n practice greeting-route -o jsonpath='{.spec.to.name}'
    equals: greeting
  - desc: TLS termination is edge
    run: oc get route -n practice greeting-route -o jsonpath='{.spec.tls.termination}'
    equals: edge
```

Rules:
- `checks` is a list. Every check has `run` (a shell/`oc` command) and one of:
  `equals` (string match, whitespace-trimmed), `contains`, `matches` (regex),
  `non-empty`, `exit-success`, `not-equals`.
- The grader runs checks **in order**; a check fails if the command exits
  non-zero or the expectation fails. A question is passed only if all checks
  pass (points split evenly across checks so partial credit is possible).
- `solution` is displayed in Training and on the score screen.
- Optional `setup` on a question: a list of `oc apply`/shell commands run by
  the conductor before grading (used to restore the task's starting state).

## Grading rules

- Knowledge: correct = 1.0, wrong = 0.0 (v1 single-select).
- Hands-on: `points * passed_checks / total_checks`.
- Attempt percentage = earned / total possible. Pass if >= `pass_threshold`.
- Domain weakness = mean score per domain; reported weakest-first.

## Validator (`ga validate`)

The validator enforces: bank metadata complete; domains sum to 1.0; draw_size
>= available questions in every domain; each question well-formed; answer key
present in options; hands-on questions have >= 1 check and a runnable command;
no duplicate question ids; YAML parses. It exits non-zero on any error.
