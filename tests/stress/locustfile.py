"""
VFR Outlook API — Locust stress test suite.

Scenarios
---------
  BaselineUser      — single-airport forecasts, search, health check (low weight)
  RegionUser        — /region fan-out queries across dense and sparse airports
  TripUser          — /trip corridor queries of varying length
  SpikeUser         — identical to RegionUser; used in spike / burst runs
  SoakUser          — mixed long-running queries for memory / drift detection

Usage
-----
  # Interactive web UI (open http://localhost:8089)
  locust -f tests/stress/locustfile.py --host https://vfr.broken-top.com

  # Headless baseline (1 user, 2 minutes)
  locust -f tests/stress/locustfile.py --headless -u 1 -r 1 \
         --run-time 2m --tags baseline \
         --host https://vfr.broken-top.com \
         --html tests/stress/reports/baseline.html

  # Fan-out load (20 users, 5 minutes)
  locust -f tests/stress/locustfile.py --headless -u 20 -r 1 \
         --run-time 5m --tags fan-out \
         --host https://vfr.broken-top.com \
         --html tests/stress/reports/fan-out.html

  # Spike test (50 users, 90 seconds)
  locust -f tests/stress/locustfile.py --headless -u 50 -r 5 \
         --run-time 90s --tags spike \
         --host https://vfr.broken-top.com \
         --html tests/stress/reports/spike.html

  # Soak test (10 users, 30 minutes)
  locust -f tests/stress/locustfile.py --headless -u 10 -r 1 \
         --run-time 30m --tags soak \
         --host https://vfr.broken-top.com \
         --html tests/stress/reports/soak.html

  # Cache effectiveness (run twice within 30 min to observe hit rate change)
  locust -f tests/stress/locustfile.py --headless -u 10 -r 2 \
         --run-time 3m --tags cache \
         --host https://vfr.broken-top.com \
         --html tests/stress/reports/cache-round1.html
"""

import json
import os
import random
import time
from pathlib import Path

from locust import HttpUser, between, tag, task, events
from locust.runners import MasterRunner, WorkerRunner

# ---------------------------------------------------------------------------
# Load fixture data
# ---------------------------------------------------------------------------
_FIXTURES_PATH = Path(__file__).parent / "fixtures" / "airports.json"
with open(_FIXTURES_PATH) as f:
    _FIXTURES = json.load(f)

_DENSE_AIRPORTS   = [a["icao"] for a in _FIXTURES["dense"]]
_SPARSE_AIRPORTS  = [a["icao"] for a in _FIXTURES["sparse"]]
_BASELINE_AIRPORT = _FIXTURES["baseline"][0]["icao"]
_TRIPS            = _FIXTURES["trips"]
_REGION_SCENARIOS = _FIXTURES["region_scenarios"]

# ---------------------------------------------------------------------------
# Custom event listeners — log test phase transitions and summary stats
# ---------------------------------------------------------------------------

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print(f"\n[vfr-stress] Test started. Target: {environment.host}")
    print(f"[vfr-stress] Fixtures: {_FIXTURES_PATH}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.stats
    total = stats.total
    print(
        f"\n[vfr-stress] === SUMMARY ===\n"
        f"  Requests:    {total.num_requests}\n"
        f"  Failures:    {total.num_failures} "
        f"({100 * total.num_failures / max(total.num_requests, 1):.1f}%)\n"
        f"  p50 latency: {total.get_response_time_percentile(0.50):.0f} ms\n"
        f"  p95 latency: {total.get_response_time_percentile(0.95):.0f} ms\n"
        f"  p99 latency: {total.get_response_time_percentile(0.99):.0f} ms\n"
        f"  Max latency: {total.max_response_time:.0f} ms\n"
        f"  RPS (peak):  {total.total_rps:.2f}\n"
    )


# ---------------------------------------------------------------------------
# Helper: validate response has expected shape (fast sanity check)
# ---------------------------------------------------------------------------

def _check_forecast_response(response):
    """Fail the request if the response is missing expected top-level keys."""
    if response.status_code != 200:
        return  # already counted as failure by Locust
    try:
        data = response.json()
        if "daily_forecasts" not in data and "airports" not in data:
            response.failure("Response missing daily_forecasts/airports key")
    except Exception as exc:
        response.failure(f"JSON parse error: {exc}")


def _check_region_response(response):
    if response.status_code != 200:
        return
    try:
        data = response.json()
        if "airports" not in data or "airport_count" not in data:
            response.failure("Region response missing airports/airport_count key")
        elif data["airport_count"] == 0:
            response.failure("Region returned zero airports")
    except Exception as exc:
        response.failure(f"JSON parse error: {exc}")


# ---------------------------------------------------------------------------
# User classes
# ---------------------------------------------------------------------------

class BaselineUser(HttpUser):
    """
    Low-weight baseline: single airport forecast, search, and health check.
    Establishes p50/p95/p99 latency floor before load is applied.

    Tags: baseline
    """
    wait_time = between(2, 5)
    weight = 1

    @tag("baseline", "soak")
    @task(3)
    def single_airport_forecast(self):
        with self.client.get(
            f"/api/v1/airport/{_BASELINE_AIRPORT}/forecast",
            name="/api/v1/airport/[icao]/forecast",
            catch_response=True,
        ) as resp:
            _check_forecast_response(resp)

    @tag("baseline", "soak")
    @task(2)
    def airport_search(self):
        queries = ["portland", "seattle", "san jose", "bend", "den"]
        q = random.choice(queries)
        self.client.get(
            "/api/v1/airports/search",
            params={"q": q},
            name="/api/v1/airports/search",
        )

    @tag("baseline", "soak")
    @task(1)
    def health_check(self):
        self.client.get("/health", name="/health")

    @tag("baseline")
    @task(1)
    def scoring_params(self):
        self.client.get("/api/v1/scoring-params", name="/api/v1/scoring-params")


class RegionUser(HttpUser):
    """
    Primary load driver: /region fan-out queries.
    Alternates between dense (Bay Area, LA) and sparse (Oregon) airports
    to exercise both maximum outbound call counts and minimum call counts.

    Tags: fan-out, soak
    """
    wait_time = between(3, 8)
    weight = 6

    @tag("fan-out", "soak", "cache")
    @task(4)
    def region_dense_large(self):
        """Max fan-out: Bay Area at full radius + cap."""
        icao = random.choice(_DENSE_AIRPORTS)
        with self.client.get(
            "/api/v1/region",
            params={"icao": icao, "radius": 100, "max_airports": 50},
            name="/api/v1/region [dense-large]",
            timeout=60,
            catch_response=True,
        ) as resp:
            _check_region_response(resp)

    @tag("fan-out", "soak", "cache")
    @task(3)
    def region_dense_medium(self):
        """Typical production query: dense area, moderate radius."""
        icao = random.choice(_DENSE_AIRPORTS)
        with self.client.get(
            "/api/v1/region",
            params={"icao": icao, "radius": 50, "max_airports": 20},
            name="/api/v1/region [dense-medium]",
            timeout=45,
            catch_response=True,
        ) as resp:
            _check_region_response(resp)

    @tag("fan-out", "soak")
    @task(2)
    def region_sparse(self):
        """Sparse area: few external calls, tests latency floor."""
        icao = random.choice(_SPARSE_AIRPORTS)
        with self.client.get(
            "/api/v1/region",
            params={"icao": icao, "radius": 150, "max_airports": 20},
            name="/api/v1/region [sparse]",
            timeout=45,
            catch_response=True,
        ) as resp:
            _check_region_response(resp)

    @tag("fan-out")
    @task(1)
    def region_max_cap(self):
        """Absolute worst case: LA basin at full cap."""
        with self.client.get(
            "/api/v1/region",
            params={"icao": "KBUR", "radius": 75, "max_airports": 50},
            name="/api/v1/region [la-max]",
            timeout=90,
            catch_response=True,
        ) as resp:
            _check_region_response(resp)


class TripUser(HttpUser):
    """
    /trip corridor queries: short, medium, and long routes.
    Long routes exercise the corridor airport selection algorithm and
    maximum async fan-out depth.

    Tags: fan-out, soak
    """
    wait_time = between(5, 15)
    weight = 3

    @tag("fan-out", "soak")
    @task(3)
    def trip_random(self):
        """Pick a random trip from the fixture set."""
        trip = random.choice(_TRIPS)
        with self.client.get(
            "/api/v1/trip",
            params={
                "origin": trip["origin"],
                "dest": trip["dest"],
                "corridor_width": trip["corridor_width"],
                "max_airports": 30,
            },
            name=f"/api/v1/trip [{trip['id']}]",
            timeout=120,
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                return
            try:
                data = resp.json()
                if "airports" not in data or "daily_scores" not in data:
                    resp.failure("Trip response missing airports/daily_scores")
                elif data.get("airport_count", 0) < 2:
                    resp.failure("Trip returned fewer than 2 airports")
            except Exception as exc:
                resp.failure(f"JSON parse error: {exc}")

    @tag("fan-out")
    @task(1)
    def trip_max_airports(self):
        """Long route at maximum airport cap — highest trip fan-out."""
        trip = next(t for t in _TRIPS if t["id"] == "pnw_long")
        with self.client.get(
            "/api/v1/trip",
            params={
                "origin": trip["origin"],
                "dest": trip["dest"],
                "corridor_width": 100,
                "max_airports": 50,
            },
            name="/api/v1/trip [max-airports]",
            timeout=180,
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                return
            try:
                data = resp.json()
                if data.get("airport_count", 0) < 2:
                    resp.failure("Max-airports trip returned fewer than 2 airports")
            except Exception as exc:
                resp.failure(f"JSON parse error: {exc}")


class SpikeUser(HttpUser):
    """
    Mirrors RegionUser but with no wait time for spike/burst scenarios.
    Used exclusively in spike tests — do not mix with soak or baseline runs.

    Tags: spike
    """
    wait_time = between(0.5, 2)
    weight = 10

    @tag("spike")
    @task(5)
    def region_spike_dense(self):
        icao = random.choice(_DENSE_AIRPORTS)
        with self.client.get(
            "/api/v1/region",
            params={"icao": icao, "radius": 100, "max_airports": 50},
            name="/api/v1/region [spike-dense]",
            timeout=60,
            catch_response=True,
        ) as resp:
            _check_region_response(resp)

    @tag("spike")
    @task(2)
    def airport_spike(self):
        with self.client.get(
            f"/api/v1/airport/{_BASELINE_AIRPORT}/forecast",
            name="/api/v1/airport/[icao]/forecast [spike]",
            timeout=30,
            catch_response=True,
        ) as resp:
            _check_forecast_response(resp)

    @tag("spike")
    @task(1)
    def health_spike(self):
        self.client.get("/health", name="/health [spike]")


class SoakUser(HttpUser):
    """
    Mixed long-running queries for memory leak and response time drift detection.
    Slow wait times to keep sustained RPS moderate (not hammering).

    Tags: soak
    """
    wait_time = between(8, 20)
    weight = 2

    @tag("soak")
    @task(6)
    def soak_region(self):
        icao = random.choice(_DENSE_AIRPORTS + _SPARSE_AIRPORTS)
        radius = random.choice([50, 75, 100, 150])
        max_airports = random.choice([10, 20, 30])
        with self.client.get(
            "/api/v1/region",
            params={"icao": icao, "radius": radius, "max_airports": max_airports},
            name="/api/v1/region [soak]",
            timeout=60,
            catch_response=True,
        ) as resp:
            _check_region_response(resp)

    @tag("soak")
    @task(3)
    def soak_trip(self):
        trip = random.choice(_TRIPS)
        with self.client.get(
            "/api/v1/trip",
            params={
                "origin": trip["origin"],
                "dest": trip["dest"],
                "corridor_width": trip["corridor_width"],
                "max_airports": 20,
            },
            name="/api/v1/trip [soak]",
            timeout=120,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                try:
                    resp.json()
                except Exception as exc:
                    resp.failure(f"JSON parse error: {exc}")

    @tag("soak")
    @task(1)
    def soak_health(self):
        self.client.get("/health", name="/health [soak]")
