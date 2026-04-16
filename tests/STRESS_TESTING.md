# VFR Outlook — Stress Test Guide

This document covers how to install, configure, and run the Locust-based stress test suite against the VFR Outlook API. It also describes how to interpret results using the backend instrumentation and Grafana dashboards.

---

## Prerequisites

### Install test dependencies

From the repo root:

```bash
pip install -r tests/requirements-stress.txt
```

This installs Locust (≥2.24.0). No other dependencies are needed — the suite uses only the standard library and Locust.

### Target host

All commands below use `https://vfr.broken-top.com` as the target. Replace with `http://localhost:8000` to run against a local backend instance.

To run against a local instance:

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Test Suite Overview

The suite lives in `tests/stress/locustfile.py`. It contains five user classes, each tagged so you can run scenarios in isolation:

| Class | Tag(s) | Purpose |
|-------|--------|---------|
| `BaselineUser` | `baseline`, `soak` | Single airport forecasts, search, health check. Establishes the latency floor. |
| `RegionUser` | `fan-out`, `soak`, `cache` | `/region` fan-out queries at varying radii across dense (Bay Area, LA) and sparse (Oregon) airports. Primary load driver. |
| `TripUser` | `fan-out`, `soak` | `/trip` corridor queries — short (PDX→SEA), medium (SJC→LAX), long (SEA→DEN). |
| `SpikeUser` | `spike` | Same as `RegionUser` but with minimal wait time. Used only for burst/spike runs. |
| `SoakUser` | `soak` | Mixed, slow-paced queries over 30+ minutes. Surfaces memory leaks and response time drift. |

Test airport fixtures (ICAO codes, density profiles, trip routes) are in `tests/stress/fixtures/airports.json`.

---

## Running Tests

### Interactive mode (web UI)

Launches a browser UI at `http://localhost:8089` where you can set user count and spawn rate interactively and watch metrics in real time.

```bash
locust -f tests/stress/locustfile.py \
       --host https://vfr.broken-top.com
```

Open `http://localhost:8089`, enter the desired user count and spawn rate, then click **Start**.

---

### Headless mode (CI / scripted runs)

All headless runs write an HTML report to `tests/stress/reports/`. That directory is gitignored — reports are not committed.

#### 1. Baseline

Establishes p50/p95/p99 latency with a single user before any load is applied. Run this first to get a clean reference point.

```bash
locust -f tests/stress/locustfile.py --headless \
       -u 1 -r 1 --run-time 2m \
       --tags baseline \
       --host https://vfr.broken-top.com \
       --html tests/stress/reports/baseline.html
```

**What to look for:** p99 < 3 s for `/airport/[icao]/forecast`, p99 < 10 s for `/region`. Anything higher indicates a cold external API or network issue before load even starts.

---

#### 2. Fan-out load test

Ramps to 20 concurrent users over 20 seconds and holds for 5 minutes. Mixes `/region` (dense and sparse) and `/trip` queries. This is the primary bottleneck-finding run.

```bash
locust -f tests/stress/locustfile.py --headless \
       -u 20 -r 1 --run-time 5m \
       --tags fan-out \
       --host https://vfr.broken-top.com \
       --html tests/stress/reports/fan-out.html
```

**What to look for:**
- Error rate > 1% (likely 429s or timeouts from external weather APIs)
- p99 > 20 s on `/region [dense-large]` (indicates NOAA or Aviation Weather throttling)
- `vfr.external.rate_limit` counter spiking in Grafana

---

#### 3. Spike test

Ramps to 50 users in 10 seconds (rate=5), holds for 90 seconds, then stops. Finds the failure mode under a sudden traffic surge.

```bash
locust -f tests/stress/locustfile.py --headless \
       -u 50 -r 5 --run-time 90s \
       --tags spike \
       --host https://vfr.broken-top.com \
       --html tests/stress/reports/spike.html
```

**What to look for:**
- Request error rate during the ramp phase (first 10 s)
- Whether the service recovers after the spike ends
- `vfr.region.inflight_airports` gauge in Grafana — should not exceed ~40 concurrently

---

#### 4. Cache effectiveness test

Run twice in succession (within 30 minutes) to measure how much the Open-Meteo in-process cache reduces latency and external call rate on repeated region queries. Compare reports from both rounds.

**Round 1 (cold cache):**
```bash
locust -f tests/stress/locustfile.py --headless \
       -u 10 -r 2 --run-time 3m \
       --tags cache \
       --host https://vfr.broken-top.com \
       --html tests/stress/reports/cache-round1.html
```

**Round 2 (warm cache — run immediately after):**
```bash
locust -f tests/stress/locustfile.py --headless \
       -u 10 -r 2 --run-time 3m \
       --tags cache \
       --host https://vfr.broken-top.com \
       --html tests/stress/reports/cache-round2.html
```

**What to look for:** Round 2 p99 on `/region` should be meaningfully lower than Round 1. The **Open-Meteo Cache Hit Rate** stat panel in Grafana should climb above 80% during Round 2. If it stays low, the 1 km grid key is hitting too many unique cells.

---

#### 5. Soak test

10 users, mixed workload, 30 minutes. Detect memory leaks (RSS growth in k8s container metrics), response time drift over time, and in-process cache unbounded growth.

```bash
locust -f tests/stress/locustfile.py --headless \
       -u 10 -r 1 --run-time 30m \
       --tags soak \
       --host https://vfr.broken-top.com \
       --html tests/stress/reports/soak.html
```

**What to look for:**
- Response time trend increasing over the 30-minute window (drift = memory pressure or cache growth)
- Container RSS approaching the 256 MB limit — watch k8s container memory metrics in Grafana
- Advisory or Open-Meteo cache dict growing unboundedly (no eviction today — symptom is increasing p99 late in the run)

---

## Reading Reports

Each headless run produces a self-contained HTML report in `tests/stress/reports/`. Open it in a browser. Key sections:

- **Statistics table** — per-endpoint request count, failure count, p50/p95/p99/max latency, RPS
- **Charts** — requests/s and response time over the run duration
- **Failures** — error messages grouped by type (timeout, HTTP 4xx/5xx, JSON parse errors)

The console also prints a summary at the end of every run:

```
[vfr-stress] === SUMMARY ===
  Requests:    1240
  Failures:    12 (0.97%)
  p50 latency: 4823 ms
  p95 latency: 18440 ms
  p99 latency: 31200 ms
  Max latency: 45100 ms
  RPS (peak):  6.82
```

---

## Grafana Instrumentation

While a test is running, open the **VFR Outlook — Service Health** dashboard. The relevant panels for stress test analysis are in the **External API Health** row:

| Panel | What it tells you |
|-------|-------------------|
| External Call Latency p99 by Service | Which external API (`metar`, `noaa_points`, `noaa_forecast`, `open_meteo`) is the slowest under load |
| External API Rate Limit Events (429/s) | Whether you are being throttled — Aviation Weather is the most likely culprit |
| External API Timeout Rate by Service | Timeout cascades; `noaa_forecast` timeouts after `noaa_points` succeeds means NOAA is overloaded |
| Open-Meteo Cache Hit Rate | Below 50% = cache is not helping; investigate grid key diversity |
| Inflight Airport Fetches (Fan-out Depth) | Instantaneous fan-out depth — sustained values >40 indicate thundering herd risk |
| Open-Meteo Cache Hits vs Misses | Time-series view of cache effectiveness across cache-warm/cold test rounds |

For trace-level investigation, use the **Distributed Traces** row to click into individual slow requests and see the full NOAA two-step span tree (`weather.noaa_points_lookup` → `weather.noaa_forecast_fetch`).

---

## Known Bottlenecks and Mitigations

These are the failure modes the tests are designed to surface, in priority order:

### 1. NOAA sequential 2-step (highest impact)
**Symptom:** `weather.noaa_points_lookup` span completes but `weather.noaa_forecast_fetch` adds another 2–8 s.  
**Fix:** Cache the `(lat, lon) → forecast URL` mapping with a 24-hour TTL. The forecast URL for a given grid point changes at most once a day.

### 2. Aviation Weather 429 rate limiting
**Symptom:** `vfr.external.rate_limit{service="metar"}` counter climbs during fan-out runs.  
**Fix:** Add exponential backoff with jitter on 429 responses, or cache METAR results for 5 minutes (acceptable staleness for the forecast use case).

### 3. In-process cache isolation between replicas
**Symptom:** Round 2 cache hit rate stays low even for identical region queries. Occurs when the k8s load balancer routes the two requests to different pod replicas.  
**Fix:** Move Open-Meteo and advisory caches to Redis/Valkey so all replicas share a single cache.

### 4. Memory limit (256 MB pod cap)
**Symptom:** RSS grows steadily during soak test; pod OOM-killed late in the run.  
**Fix:** Bound the `_om_cache` dict by entry count (e.g., LRU eviction after 500 entries) or raise the pod memory limit to 512 MB.

### 5. O(n) airport scan under wide radius
**Symptom:** `airports_within_radius` time grows with radius; visible as pre-fan-out latency in the `region_forecast` span.  
**Fix:** Pre-build a `scipy.spatial.KDTree` at startup for O(log n) range queries over the 12k airport dataset.

---

## File Layout

```
tests/
  STRESS_TESTING.md            # This document
  requirements-stress.txt      # pip install -r this
  stress/
    locustfile.py              # All Locust user classes and scenarios
    .gitignore                 # Excludes reports/*.html and *.csv
    fixtures/
      airports.json            # Test airport set with density and trip metadata
    reports/                   # Generated HTML reports (gitignored)
```
