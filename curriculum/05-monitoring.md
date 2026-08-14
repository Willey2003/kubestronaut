# Module 5 — Monitoring (Prometheus + Grafana)

Module 5 is the **CPNA** track: observability with Prometheus and Grafana —
what to scrape, how to query, how to alert, and how to build dashboards. It is
the last module for a reason: you monitor the workloads and clusters you have
already learned to build, administer, and secure.

## Learning objectives

1. Explain the observability pillars (metrics, logs, traces) and Prometheus's
   pull-based architecture.
2. Configure scrape targets — static, file-based, and Kubernetes service
   discovery — with relabelling and metric filtering.
3. Write PromQL: instant and range queries, `rate`, aggregation by labels, and
   histogram quantiles.
4. Define recording and alerting rules and route alerts through
   Alertmanager.
5. Operate Grafana: add a Prometheus datasource, build panels and dashboards
   with variables, and understand basic alerting in Grafana.
6. Reason about SLOs/SLIs, golden signals, and when to use the Pushgateway.

## Key concepts

- **Observability pillars**: metrics (numbers over time), logs (events), and
  traces (request flow across services). Prometheus/Grafana are a metrics
  platform; logs/traces (Loki, Tempo/OTel) complement it — the CPNA track
  focuses on metrics and their SLO story.
- **Metrics model**: every metric is a named series of label values with
  timestamps. Four types: **counter** (only increases: requests), **gauge**
  (up and down: temperature, queue depth), **histogram** (bucketed
  observations for latency percentiles), **summary** (client-side quantiles).
- **Pull model**: Prometheus scrapes exporters over HTTP (`/metrics`). This
  makes targets discoverable, keeps push out of the loop, and is what
  distinguishes Prometheus from push-based agents. Scrape failures surface
  instantly in `up == 0`.
- **Exporters**: small services that translate system metrics into Prometheus
  format — `node_exporter` for OS metrics, `kube-state-metrics` for cluster
  object state, `blackbox_exporter` for HTTP/DNS probes, and application
  `/metrics` endpoints.
- **scrape_configs**: the Prometheus config's `scrape_interval`, targets
  (static lists, file-based, or `kubernetes_sd_configs`), plus `relabel_configs`
  and `metric_relabel_configs` to rename, add, or drop labels and metrics.
  Target health is `up{job="...", instance="..."}`.
- **Service discovery in Kubernetes**: scrape annotations
  (`prometheus.io/scrape: "true"`) or the prometheus-operator CRDs —
  `ServiceMonitor`/`PodMonitor` select what to scrape by label, which the
  operator turns into `scrape_configs`.
- **PromQL selectors**: `http_requests_total{job="web", code="500"}` filters by
  label; `job=~"web.*"` regexes; `{__name__=~".*errors.*"}` matches metric
  names. Instant vectors are a single value per series; range vectors
  (`[5m]`) carry a time window for `rate`.
- **rate and aggregations**: `rate(counter[5m])` computes per-second growth
  (always use `rate` on counters); `sum by (namespace) (rate(...))`,
  `avg`, `max`, `topk` group series. `increase(counter[1h])` is `rate`
  multiplied by the window.
- **Histograms and percentiles**: `histogram_quantile(0.99, rate(apiserver_
  request_duration_seconds_bucket[5m]))` turns bucket counters into latency
  percentiles — the standard way to report SLO-relevant p99 latency.
- **Recording rules**: precompute expensive or reused queries as new series
  (`job:http_requests:rate5m = rate(...)`), evaluated on a rule interval. This
  keeps dashboards and alerts fast and consistent.
- **Alerting rules**: a PromQL expression plus `for` (duration before firing)
  and labels/annotations. Firing alerts are sent to **Alertmanager**, which
  groups, deduplicates, throttles, and routes them (severity, team) to
  receivers (webhook, Slack, PagerDuty, email).
- **Grafana**: the dashboard layer on top of Prometheus — datasources
  (Prometheus by URL), panels (each a PromQL query), and dashboards with
  templated variables (`$namespace`) so one dashboard serves many
  environments.
- **SLOs and golden signals**: the four golden signals — latency, traffic,
  errors, saturation — and the SLI→SLO chain (measure, target, error budget).
  The Prometheus `sli` conventions and recording rules turn `sum(rate(...))`
  queries into budget burn-down panels.
- **Pushgateway**: an exception for short-lived batch jobs whose metrics
  would vanish between scrapes; it receives pushes from one-shot jobs. It is
  not for metrics that survive — prefer pull for always-on services.

## Hands-on exercises

These assume a Prometheus + Grafana stack is deployed (the standard route is
`kube-prometheus-stack` via Helm in namespace `monitoring`), and that you can
reach the APIs with `kubectl port-forward`. Adjust service names to your
installation.

```sh
kubectl get pods -n monitoring
kubectl -n monitoring port-forward svc/prometheus-operated 9090:9090 &
kubectl -n monitoring port-forward svc/grafana 3000:3000 &
```

### Exercise 1 — Targets up, metrics flowing

- Task: confirm Prometheus is scraping its own targets and that a known metric
  exists.
- Expected outcome: `up` returns 1 for several targets, and
  `prometheus_tsdb_head_series` exists with a value.

```sh
curl -s 'http://localhost:9090/api/v1/query?query=up' | jq '.data.result | length'
curl -s 'http://localhost:9090/api/v1/query?query=count(up)' | jq -r '.data.result[0].value[1]'
curl -s 'http://localhost:9090/api/v1/query?query=prometheus_tsdb_head_series' | jq '.data.result'
```

- Verification (non-empty result; `up == 1` rows present):

```sh
curl -s 'http://localhost:9090/api/v1/query?query=up{job="prometheus"}' | jq -r '.data.result[].value[1]'
curl -s 'http://localhost:9090/api/v1/targets' | jq -r '.data.activeTargets[] | [.labels.job, .health] | @tsv'
```

### Exercise 2 — Node and kube metrics

- Task: pull OS and cluster-object metrics from the exporters.
- Expected outcome: `node_memory_MemTotal_bytes` and `kube_node_info` return
  one series per node, and CPU utilisation is computable.

```sh
curl -s 'http://localhost:9090/api/v1/query?query=node_memory_MemTotal_bytes' | jq '.data.result[].value[1]'
curl -s 'http://localhost:9090/api/v1/query?query=kube_node_info' | jq -r '.data.result[].metric.node'
curl -s 'http://localhost:9090/api/v1/query?query=100%20-%20avg%20by%20(instance)%20(rate(node_cpu_seconds_total{mode="idle"}[5m]))*100' | jq '.data.result'
```

- Verification (one series per node; idle-CPU expression yields 0–100):

```sh
curl -s 'http://localhost:9090/api/v1/query?query=node_memory_MemTotal_bytes' | jq -r '.data.result[].metric.instance'
```

### Exercise 3 — PromQL: rate, grouping, percentiles

- Task: query a counter as a rate grouped by namespace, and compute a p99
  latency from a histogram.
- Expected outcome: per-namespace container CPU rates, and a single p99 value
  from the apiserver request-duration histogram.

```sh
curl -s 'http://localhost:9090/api/v1/query?query=sum%20by%20(namespace)%20(rate(container_cpu_usage_seconds_total{container!=""}[5m]))' | jq '.data.result'
curl -s 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.99,%20rate(apiserver_request_duration_seconds_bucket[5m]))' | jq '.data.result'
```

- Verification (grouped result has non-empty `metric.namespace`; the quantile
  is a plausible number of seconds):

```sh
curl -s 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.99,%20sum%20by%20(le)%20(rate(apiserver_request_duration_seconds_bucket[5m])))' | jq '.data.result[0].value[1]'
```

### Exercise 4 — Alerting rule that actually fires

- Task: add a recording rule for request rate and an alerting rule that fires
  when a target is down for 1 minute; verify the rule group loads and the
  alert becomes pending/firing.
- Expected outcome: after a reload, `up{job="nonexistent"}` is 0 and the
  alert `TargetDown` (or a custom one) appears in `ALERTS`.

```sh
kubectl exec -n monitoring prometheus-kube-prometheus-prometheus-0 -- sh -c \
  'curl -s -X POST http://localhost:9090/-/reload'
curl -s 'http://localhost:9090/api/v1/rules' | jq -r '.data.groups[].rules[].name' | head
curl -s 'http://localhost:9090/api/v1/query?query=ALERTS' | jq '.data.result | length'
```

- Verification (rule names list includes your recording/alerting rules;
  `ALERTS` non-empty when a rule fires):

```sh
curl -s 'http://localhost:9090/api/v1/rules?type=alert' | jq -r '.data.groups[].rules[] | select(.state=="firing") | .name'
```

### Exercise 5 — Grafana: datasource, panel, variable

- Task: confirm the Prometheus datasource is registered in Grafana, then build
  a dashboard with one panel (node CPU) that is templated on an instance
  variable.
- Expected outcome: `/api/datasources` lists a Prometheus source; the created
  dashboard exists with one panel and a variable.

```sh
curl -s -u admin:admin 'http://localhost:3000/api/datasources' | jq -r '.[].type'
curl -s -u admin:admin 'http://localhost:3000/api/datasources' | jq -r '.[].url'
curl -s -u admin:admin 'http://localhost:3000/api/dashboards/home' | jq -r '.meta.slug'
curl -s -u admin:admin -X POST 'http://localhost:3000/api/dashboards/db' \
  -H 'Content-Type: application/json' \
  -d '{"dashboard":{"title":"Node CPU","panels":[{"type":"timeseries","title":"CPU %","datasource":"Prometheus","targets":[{"expr":"100 - avg(rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) by (instance) * 100","refId":"A"}],"gridPos":{"h":8,"w":12,"x":0,"y":0}}],"templating":{"list":[{"name":"instance","type":"query","query":"label_values(node_cpu_seconds_total, instance)"}]}},"overwrite":true}' \
  | jq -r '.status'
```

- Verification (datasource list non-empty; dashboard POST returns `"success"`):

```sh
curl -s -u admin:admin 'http://localhost:3000/api/search?query=Node%20CPU' | jq -r '.[].title'
curl -s 'http://localhost:9090/api/v1/label/instance/values' | jq '.data | length'
```

## Test yourself

When you can do Exercises 1–5 without the book, sit simulator attempts on
`banks/cpna`:

- **First pass**: **Training**, `focus_domain = metrics-collection` — scrape
  config and service discovery.
- **Second pass**: **Training**, `focus_domain = promql` — read every
  explanation; PromQL is where CPNA scores are won or lost.
- **Third pass**: **Mastery**, `focus_domain = grafana`.
- **Fourth pass**: **Mastery**, `focus_domain = alerting` (recording rules,
  Alertmanager, SLOs).
- **Final pass**: full-bank **Mastery**, timed to the bank's
  `duration_minutes`.

If `promql` shows weak on the report, redo Exercise 3 with every aggregation
clause you can think of (`sum by`, `avg without`, `topk`, `histogram_quantile`)
until the API responses are second nature.

## See also

- The Prometheus and Grafana certification/training pages on
  linuxfoundation.org and prometheus.io (referenced by name).
- [Curriculum index](README.md) — back to the path overview, schedule, and
  `focus_domain` vocabulary.
