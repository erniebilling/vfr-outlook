# Distributed Tracing Setup — Ingress to Service

This document describes every Kubernetes resource that must be configured to get
end-to-end distributed traces flowing from Traefik (ingress) through to the
application backend, with all spans visible in Grafana Tempo under a single trace ID.

## Stack

| Component | Role |
|-----------|------|
| Traefik v3 (k3s built-in) | Ingress controller — root span |
| OpenTelemetry Collector | Receives OTLP spans/metrics, forwards to Tempo/Prometheus |
| Grafana Tempo | Trace storage and query backend |
| Grafana | Trace visualization (Explore → Tempo datasource) |
| FastAPI + `opentelemetry-sdk` | Application instrumentation |

---

## 1. Tempo Deployment

Tempo must have enough memory to buffer traces or it will OOMKill, causing the
collector's gRPC connection to be refused and traces to be lost.

**Minimum resource limits (tested on Raspberry Pi 5 cluster):**

```yaml
resources:
  requests:
    cpu: 100m
    memory: 512Mi
  limits:
    cpu: 500m
    memory: 1Gi   # Do NOT go below 1Gi — 512Mi causes OOMKill under load
```

Tempo must listen on both gRPC (4317) and HTTP (4318) OTLP ports so the collector
can forward spans to it:

```yaml
# tempo-config ConfigMap
server:
  http_listen_port: 3200

distributor:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317
        http:
          endpoint: 0.0.0.0:4318

storage:
  trace:
    backend: local
    local:
      path: /var/tempo/traces
    wal:
      path: /var/tempo/wal

compactor:
  compaction:
    block_retention: 168h
```

---

## 2. OpenTelemetry Collector

The collector must accept OTLP on both gRPC (4317) and HTTP (4318) — gRPC for the
application backend, HTTP for Traefik (Traefik's HTTP OTLP exporter works reliably
whereas gRPC has a silent failure mode when both transports are configured).

```yaml
# otel-collector-config ConfigMap
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 5s
    send_batch_size: 1000
  memory_limiter:
    check_interval: 1s
    limit_mib: 256

exporters:
  otlp/tempo:
    endpoint: tempo:4317
    tls:
      insecure: true

  prometheus:
    endpoint: 0.0.0.0:8889
    namespace: otel   # produces otel_* prefixed metric names in Prometheus

  loki:
    endpoint: http://loki:3100/loki/api/v1/push

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp/tempo]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [prometheus]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [loki]
```

The collector's Service must expose ports 4317 (gRPC) and 4318 (HTTP) as ClusterIP
so both Traefik (in `kube-system`) and the application backend can reach it.

---

## 3. Traefik — HelmChartConfig (k3s)

On k3s, Traefik is managed by Helm. Use a `HelmChartConfig` resource to inject
tracing configuration without modifying the k3s-managed HelmChart directly.

**Critical lessons learned:**

- Use **HTTP OTLP** (`--tracing.otlp.http.*`), not gRPC. When both gRPC and HTTP
  are configured, Traefik v3 may silently fail to export via gRPC while the HTTP
  endpoint also fails (defaults to `https://localhost:4318`). Only configure one
  transport.
- `--tracing.addinternals=true` enables spans for Traefik's internal routers
  (ping, metrics). Without it, only external router spans are emitted.
- The `tracing.otlp.enabled: true` Helm chart value does NOT translate to the
  correct CLI flags for gRPC sub-keys — use `additionalArguments` for all tracing
  flags to ensure exact CLI flag mapping.

```yaml
# k8s/traefik-helm-config.yaml
apiVersion: helm.cattle.io/v1
kind: HelmChartConfig
metadata:
  name: traefik
  namespace: kube-system
spec:
  valuesContent: |-
    additionalArguments:
      - "--tracing.otlp.http.endpoint=http://otel-collector.monitoring:4318/v1/traces"
      - "--tracing.otlp.http.tls.insecureskipverify=true"
      - "--tracing.samplerate=1.0"
      - "--tracing.servicename=traefik"
      - "--tracing.addinternals=true"
```

Apply with:
```bash
kubectl apply -f k8s/traefik-helm-config.yaml
```

k3s will automatically trigger a Helm upgrade within ~30 seconds. Verify the args
were applied:
```bash
kubectl get deployment traefik -n kube-system \
  -o jsonpath='{.spec.template.spec.containers[0].args}' | tr ',' '\n' | grep trac
```

---

## 4. Kubernetes Ingress — Tracing Annotation

By default, Traefik v3 creates `TracingEntryPoint` middleware for all entrypoints
but does NOT attach `TracingRouter` middleware to routes defined via the Kubernetes
Ingress provider. Without `TracingRouter`, Traefik does not inject the W3C
`traceparent` header into upstream requests, so the backend creates a new root span
instead of continuing the Traefik trace.

**Fix:** Add the `traefik.ingress.kubernetes.io/router.observability.tracing: "true"`
annotation to the Ingress resource.

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: vfr-outlook
  namespace: vfr-outlook
  annotations:
    metallb.universe.tf/address-pool: pool
    traefik.ingress.kubernetes.io/router.observability.tracing: "true"  # <-- required
spec:
  ingressClassName: traefik
  rules:
    - host: vfr.broken-top.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: vfr-backend
                port:
                  number: 8000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: vfr-frontend
                port:
                  number: 80
```

Without this annotation, Traefik and backend traces appear as **separate unlinked
traces** in Tempo, and backend spans show `<root span not yet received>`.

---

## 5. Application Backend — OTel SDK Configuration

The FastAPI backend must initialize the OTel SDK before any imports that create
instrumented clients (httpx, etc.). Key points:

- Configure both `TracerProvider` and `MeterProvider` pointing at the collector's
  gRPC endpoint (`otel-collector.<namespace>:4317`).
- Use `FastAPIInstrumentor` with `excluded_urls="/health"` to suppress health probe
  spans — without this, liveness/readiness probes (every 5–30s) flood Tempo with
  hundreds of trivial traces and can cause Tempo OOM.
- Use `HTTPXClientInstrumentor` to propagate trace context to outbound HTTP calls
  (weather APIs), making them child spans of the incoming request span.

```python
# backend/otel.py (key settings)
_DEFAULT_OTLP_ENDPOINT = "http://otel-collector.monitoring:4317"

# backend/main.py
FastAPIInstrumentor.instrument_app(app, excluded_urls="/health")
HTTPXClientInstrumentor().instrument()
```

Backend deployment env vars:
```yaml
env:
  - name: OTEL_EXPORTER_OTLP_ENDPOINT
    value: "http://otel-collector.monitoring:4317"
  - name: OTEL_SERVICE_NAME
    value: "vfr-outlook-backend"
  - name: OTEL_DEPLOYMENT_ENV
    value: "production"
```

---

## 6. Verification Steps

After applying all of the above, verify the full pipeline:

### Check Traefik is emitting spans
```bash
# Port-forward to collector's self-telemetry port
kubectl port-forward -n monitoring pod/<otel-collector-pod> 8888:8888

# Check accepted spans by transport
curl -s http://localhost:8888/metrics | grep otelcol_receiver_accepted_spans
# Should show both transport="grpc" (backend) and transport="http" (traefik)
```

### Check Tempo is receiving traces
```bash
kubectl port-forward -n monitoring svc/tempo 3200:3200

# List service names — both "traefik" and "vfr-outlook-backend" must appear
curl -s http://localhost:3200/api/search/tags | python3 -m json.tool | grep service

# Search for recent traces — root service should be "traefik"
curl -s "http://localhost:3200/api/search?limit=5" | python3 -c "
import sys, json
for t in json.load(sys.stdin).get('traces', []):
    print(t['rootServiceName'], t['rootTraceName'], t['traceID'])
"
```

### Verify end-to-end linkage
A correctly linked trace will have both `traefik` and `vfr-outlook-backend` spans
under the **same trace ID**:
```bash
curl -s http://localhost:3200/api/traces/<traceID> | python3 -c "
import sys, json, base64
for batch in json.load(sys.stdin).get('batches', []):
    svc = next((a['value']['stringValue'] for a in batch['resource']['attributes'] if a['key']=='service.name'), '?')
    for scope in batch.get('scopeSpans', []):
        for span in scope.get('spans', []):
            print(svc, span['name'])
"
# Should print lines from both 'traefik' and 'vfr-outlook-backend'
```

---

## 7. Common Failure Modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `<root span not yet received>` in Tempo | Traefik injects `traceparent` but its spans are in a separate trace | Add `traefik.ingress.kubernetes.io/router.observability.tracing: "true"` to Ingress |
| Traefik not in service name dropdown | Traefik's OTLP exporter silently failing | Use HTTP OTLP (`--tracing.otlp.http.*`), not gRPC |
| OTel Collector `connection refused` to Tempo | Tempo OOMKilled | Increase Tempo memory limit to at least `1Gi` |
| No metrics in Prometheus | ServiceMonitor not in Prometheus allowlist | Ensure Prometheus CR `serviceMonitorSelector` includes the OTel collector ServiceMonitor |
| `exported_job` vs `job` label mismatch | Prometheus renames `job` attribute to `exported_job` | Use `{exported_job=~"$var"}` in PromQL, not `{job=~"$var"}` |
| Health probe spans flooding Tempo | FastAPIInstrumentor traces every `/health` call | Use `FastAPIInstrumentor.instrument_app(app, excluded_urls="/health")` |
