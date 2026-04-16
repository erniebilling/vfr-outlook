"""
Weather data fetching service.
Aggregates METAR (current), NOAA hourly (days 0-7), and Open-Meteo (days 0-16).
"""

import asyncio
import logging
import time
import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional

from models.forecast import DayForecast, AirportForecast, Advisory, Runway
from services.scorer import compute_vfr_score
from services.advisories import get_advisories_for_point
from otel import get_meter, get_tracer

_log = logging.getLogger(__name__)

_meter = get_meter("vfr-outlook.services.weather")
_tracer = get_tracer("vfr-outlook.services.weather")

# ---------------------------------------------------------------------------
# METAR cache — keyed on ICAO, TTL 10 minutes.
# METARs update roughly once an hour; 10 min keeps data fresh while
# collapsing the fan-out burst from region/trip queries.
# ---------------------------------------------------------------------------
_METAR_CACHE_TTL_S = 600  # 10 minutes
_metar_cache: dict[str, tuple[float, Optional[dict]]] = {}
# value: (fetched_at_monotonic, data)
_metar_cache_locks: dict[str, asyncio.Lock] = {}

# Semaphore: at most 5 METAR fetches in-flight at once across the process.
# Converts a 50-airport fan-out into ~10 serial batches instead of a
# simultaneous 50-request burst that triggers 429s on aviationweather.gov.
_METAR_CONCURRENCY = 5
_metar_semaphore = asyncio.Semaphore(_METAR_CONCURRENCY)

# ---------------------------------------------------------------------------
# Open-Meteo cache — keyed on (lat_2dp, lon_2dp), TTL 30 minutes.
# Rounds coordinates to ~1 km grid so nearby airports share one fetch,
# eliminating the per-airport burst that triggers 429s on region queries.
# ---------------------------------------------------------------------------
_OM_CACHE_TTL_S = 1800  # 30 minutes
_om_cache: dict[tuple[float, float], tuple[float, Optional[dict]]] = {}
# value: (fetched_at_monotonic, data)
_om_cache_locks: dict[tuple[float, float], asyncio.Lock] = {}

# ── Existing metrics ─────────────────────────────────────────────────────────
_forecast_requests = _meter.create_counter(
    "vfr.forecast.requests",
    description="Total number of single-airport forecast computations",
    unit="1",
)
_forecast_duration = _meter.create_histogram(
    "vfr.forecast.duration",
    description="Time to compute a single-airport forecast",
    unit="ms",
)

# ── New stress-test / bottleneck metrics ─────────────────────────────────────

# Per-external-call duration histograms (service = metar | noaa_points | noaa_forecast | open_meteo)
_external_call_duration = _meter.create_histogram(
    "vfr.external.duration",
    description="Latency of individual outbound weather API calls",
    unit="ms",
)

# Rate-limit (HTTP 429) events per external service
_rate_limit_counter = _meter.create_counter(
    "vfr.external.rate_limit",
    description="HTTP 429 responses received from external weather APIs",
    unit="1",
)

# Timeout events per external service
_timeout_counter = _meter.create_counter(
    "vfr.external.timeout",
    description="Timeout errors on external weather API calls",
    unit="1",
)

# Other (non-429, non-timeout) errors per external service
_error_counter = _meter.create_counter(
    "vfr.external.error",
    description="Non-timeout, non-429 errors on external weather API calls",
    unit="1",
)

# Cache hit / miss counters (service label distinguishes metar vs open_meteo)
_cache_hit_counter = _meter.create_counter(
    "vfr.cache.hit",
    description="In-process cache hits (metar, open_meteo)",
    unit="1",
)
_cache_miss_counter = _meter.create_counter(
    "vfr.cache.miss",
    description="In-process cache misses (metar, open_meteo)",
    unit="1",
)

# Fan-out depth: how many airport forecasts are in-flight concurrently
_inflight_airports = _meter.create_up_down_counter(
    "vfr.region.inflight_airports",
    description="Number of airport forecasts currently being fetched (fan-out depth)",
    unit="1",
)


AVIATION_WEATHER_BASE = "https://aviationweather.gov/api/data"
NOAA_POINTS_BASE = "https://api.weather.gov/points"
OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"

NOAA_HEADERS = {"User-Agent": "VFRWatch/1.0 (https://github.com/vfr-outlook)"}

# Confidence tiers by forecast day offset from today
def _confidence(day_offset: int) -> str:
    if day_offset <= 3:
        return "high"
    elif day_offset <= 7:
        return "medium"
    return "low"


async def fetch_metar(client: httpx.AsyncClient, icao: str) -> Optional[dict]:
    attrs = {"service": "metar", "icao": icao}

    # ── Cache check (outside lock for fast path) ─────────────────────────────
    fetched_at, cached = _metar_cache.get(icao, (0.0, None))
    if time.monotonic() - fetched_at < _METAR_CACHE_TTL_S:
        _cache_hit_counter.add(1, attrs)
        return cached

    if icao not in _metar_cache_locks:
        _metar_cache_locks[icao] = asyncio.Lock()
    async with _metar_cache_locks[icao]:
        # Re-check inside lock — another coroutine may have just populated it.
        fetched_at, cached = _metar_cache.get(icao, (0.0, None))
        if time.monotonic() - fetched_at < _METAR_CACHE_TTL_S:
            _cache_hit_counter.add(1, attrs)
            return cached

        _cache_miss_counter.add(1, attrs)

        # ── Semaphore: cap concurrent outbound METAR requests ────────────────
        async with _metar_semaphore:
            t0 = time.monotonic()
            result: Optional[dict] = None
            with _tracer.start_as_current_span("weather.fetch_metar") as span:
                span.set_attribute("airport.icao", icao)
                span.set_attribute("cache.hit", False)
                span.set_attribute("external.service", "aviation_weather")
                try:
                    resp = await client.get(
                        f"{AVIATION_WEATHER_BASE}/metar",
                        params={"ids": icao, "format": "json", "taf": "false", "hours": "2"},
                        timeout=10,
                    )
                    span.set_attribute("http.status_code", resp.status_code)
                    if resp.status_code == 429:
                        _rate_limit_counter.add(1, attrs)
                        _log.warning("METAR rate-limited (429) for %s", icao)
                    else:
                        resp.raise_for_status()
                        data = resp.json()
                        _external_call_duration.record((time.monotonic() - t0) * 1000, attrs)
                        result = data[0] if data else None
                except httpx.TimeoutException as exc:
                    _timeout_counter.add(1, attrs)
                    span.set_attribute("error", True)
                    span.set_attribute("error.type", "timeout")
                    _log.warning("METAR timeout for %s: %s", icao, exc)
                except Exception as exc:
                    _error_counter.add(1, attrs)
                    span.set_attribute("error", True)
                    try:
                        payload = resp.text
                    except Exception:
                        payload = "<unavailable>"
                    _log.warning(
                        "METAR fetch failed for %s: %s | status=%s payload=%r",
                        icao,
                        exc,
                        getattr(resp, "status_code", "?"),
                        payload,
                    )
                finally:
                    _metar_cache[icao] = (time.monotonic(), result)

    return _metar_cache[icao][1]


async def fetch_noaa_hourly(client: httpx.AsyncClient, lat: float, lon: float) -> Optional[dict]:
    coord_attrs = {"service": "noaa_points", "icao": f"{lat:.2f},{lon:.2f}"}

    with _tracer.start_as_current_span("weather.fetch_noaa_hourly") as outer_span:
        outer_span.set_attribute("airport.lat", lat)
        outer_span.set_attribute("airport.lon", lon)
        outer_span.set_attribute("external.service", "noaa")

        # ── Step 1: points lookup ────────────────────────────────────────────
        t0 = time.monotonic()
        with _tracer.start_as_current_span("weather.noaa_points_lookup") as span1:
            span1.set_attribute("airport.lat", lat)
            span1.set_attribute("airport.lon", lon)
            try:
                points_resp = await client.get(
                    f"{NOAA_POINTS_BASE}/{lat:.4f},{lon:.4f}",
                    headers=NOAA_HEADERS,
                    timeout=10,
                )
                span1.set_attribute("http.status_code", points_resp.status_code)
                if points_resp.status_code == 429:
                    _rate_limit_counter.add(1, coord_attrs)
                    _log.warning("NOAA points rate-limited (429) for %.4f,%.4f", lat, lon)
                    return None
                points_resp.raise_for_status()
                forecast_url = points_resp.json()["properties"]["forecastHourly"]
                _external_call_duration.record(
                    (time.monotonic() - t0) * 1000,
                    {"service": "noaa_points", "icao": f"{lat:.2f},{lon:.2f}"},
                )
            except httpx.TimeoutException as exc:
                _timeout_counter.add(1, coord_attrs)
                span1.set_attribute("error", True)
                span1.set_attribute("error.type", "timeout")
                _log.warning("NOAA points timeout for %.4f,%.4f: %s", lat, lon, exc)
                return None
            except httpx.HTTPStatusError as exc:
                _error_counter.add(1, coord_attrs)
                span1.set_attribute("error", True)
                outer_span.set_attribute("error", True)
                _log.warning(
                    "NOAA hourly fetch failed for %.4f,%.4f: HTTP %d",
                    lat, lon, exc.response.status_code,
                )
                return None
            except Exception as exc:
                _error_counter.add(1, coord_attrs)
                span1.set_attribute("error", True)
                _log.warning("NOAA hourly fetch failed for %.4f,%.4f: %s", lat, lon, exc)
                return None

        # ── Step 2: hourly forecast fetch ────────────────────────────────────
        t1 = time.monotonic()
        forecast_attrs = {"service": "noaa_forecast", "icao": f"{lat:.2f},{lon:.2f}"}
        with _tracer.start_as_current_span("weather.noaa_forecast_fetch") as span2:
            span2.set_attribute("forecast_url", forecast_url)
            try:
                hourly_resp = await client.get(forecast_url, headers=NOAA_HEADERS, timeout=15)
                span2.set_attribute("http.status_code", hourly_resp.status_code)
                if hourly_resp.status_code == 429:
                    _rate_limit_counter.add(1, forecast_attrs)
                    _log.warning("NOAA forecast rate-limited (429) for %.4f,%.4f", lat, lon)
                    return None
                hourly_resp.raise_for_status()
                _external_call_duration.record(
                    (time.monotonic() - t1) * 1000, forecast_attrs
                )
                return hourly_resp.json()
            except httpx.TimeoutException as exc:
                _timeout_counter.add(1, forecast_attrs)
                span2.set_attribute("error", True)
                span2.set_attribute("error.type", "timeout")
                _log.warning("NOAA forecast timeout for %.4f,%.4f: %s", lat, lon, exc)
                return None
            except httpx.HTTPStatusError as exc:
                _error_counter.add(1, forecast_attrs)
                span2.set_attribute("error", True)
                _log.warning(
                    "NOAA hourly fetch failed for %.4f,%.4f: HTTP %d",
                    lat, lon, exc.response.status_code,
                )
                return None
            except Exception as exc:
                _error_counter.add(1, forecast_attrs)
                span2.set_attribute("error", True)
                _log.warning("NOAA hourly fetch failed for %.4f,%.4f: %s", lat, lon, exc)
                return None


async def fetch_open_meteo(client: httpx.AsyncClient, lat: float, lon: float) -> Optional[dict]:
    key = (round(lat, 2), round(lon, 2))
    attrs = {"service": "open_meteo", "icao": f"{key[0]},{key[1]}"}

    fetched_at, cached = _om_cache.get(key, (0.0, None))
    if time.monotonic() - fetched_at < _OM_CACHE_TTL_S:
        _cache_hit_counter.add(1, attrs)
        return cached

    if key not in _om_cache_locks:
        _om_cache_locks[key] = asyncio.Lock()
    async with _om_cache_locks[key]:
        fetched_at, cached = _om_cache.get(key, (0.0, None))
        if time.monotonic() - fetched_at < _OM_CACHE_TTL_S:
            _cache_hit_counter.add(1, attrs)
            return cached

        _cache_miss_counter.add(1, attrs)
        result: Optional[dict] = None
        t0 = time.monotonic()
        with _tracer.start_as_current_span("weather.fetch_open_meteo") as span:
            span.set_attribute("cache.hit", False)
            span.set_attribute("airport.lat", key[0])
            span.set_attribute("airport.lon", key[1])
            span.set_attribute("external.service", "open_meteo")
            try:
                resp = await client.get(
                    OPEN_METEO_BASE,
                    params={
                        "latitude": key[0],
                        "longitude": key[1],
                        "hourly": "precipitation_probability,windspeed_10m,windgusts_10m,winddirection_10m,cloudcover",
                        "forecast_days": 16,
                        "windspeed_unit": "kn",
                        "precipitation_unit": "inch",
                        "timezone": "America/Los_Angeles",
                    },
                    timeout=15,
                )
                span.set_attribute("http.status_code", resp.status_code)
                if resp.status_code == 429:
                    _rate_limit_counter.add(1, attrs)
                    _log.warning("Open-Meteo rate-limited (429) for %.2f,%.2f", key[0], key[1])
                else:
                    resp.raise_for_status()
                    result = resp.json()
                    _external_call_duration.record((time.monotonic() - t0) * 1000, attrs)
            except httpx.TimeoutException as exc:
                _timeout_counter.add(1, attrs)
                span.set_attribute("error", True)
                span.set_attribute("error.type", "timeout")
                _log.warning("Open-Meteo timeout for %.2f,%.2f: %s", key[0], key[1], exc)
            except Exception as exc:
                _error_counter.add(1, attrs)
                span.set_attribute("error", True)
                _log.warning("Open-Meteo fetch failed for %.2f,%.2f: %s", key[0], key[1], exc)
            finally:
                _om_cache[key] = (time.monotonic(), result)

    return _om_cache[key][1]


def _parse_noaa_day(hourly_data: dict, day_offset: int) -> Optional[dict]:
    """Extract average daytime conditions for a given day offset from NOAA hourly."""
    periods = hourly_data.get("properties", {}).get("periods", [])
    if not periods:
        return None

    # Target: daytime hours (8 AM – 6 PM local) for the given day
    now = datetime.now(timezone.utc)
    target_date = (now + timedelta(days=day_offset)).date()

    day_periods = [
        p for p in periods
        if target_date.isoformat() in p.get("startTime", "")
        and 8 <= int(p["startTime"][11:13]) < 18
    ]

    if not day_periods:
        return None

    winds = []
    precip_flags = []
    for p in day_periods:
        try:
            w = int(p.get("windSpeed", "0 mph").split()[0])
            winds.append(w)
        except Exception:
            pass
        forecast = p.get("shortForecast", "").lower()
        precip_flags.append(any(wx in forecast for wx in ["rain", "storm", "thunder", "shower", "snow"]))

    avg_wind = sum(winds) / len(winds) if winds else 0
    precip_pct = (sum(precip_flags) / len(precip_flags)) * 100 if precip_flags else 0

    return {
        "avg_wind": avg_wind,
        "max_gust": avg_wind * 1.3,   # NOAA doesn't give gusts in hourly; estimate
        "precip_pct": precip_pct,
        "cloud_cover": None,          # Not directly available from NOAA hourly text
        "visibility": None,
        "ceiling": None,
    }


def _avg_wind_dir(dirs: list[float]) -> Optional[int]:
    """Circular mean of wind directions."""
    import math
    if not dirs:
        return None
    sin_sum = sum(math.sin(math.radians(d)) for d in dirs)
    cos_sum = sum(math.cos(math.radians(d)) for d in dirs)
    avg = math.degrees(math.atan2(sin_sum, cos_sum)) % 360
    return round(avg)


def _parse_open_meteo_day(om_data: dict, day_offset: int) -> Optional[dict]:
    """Extract average daytime conditions for a given day offset from Open-Meteo."""
    try:
        hourly = om_data.get("hourly", {})
        times = hourly.get("time", [])
        winds = hourly.get("windspeed_10m", [])
        gusts = hourly.get("windgusts_10m", [])
        dirs  = hourly.get("winddirection_10m", [])
        precip = hourly.get("precipitation_probability", [])
        clouds = hourly.get("cloudcover", [])

        # Daytime slice: hours 8-18 for the target day
        day_start = day_offset * 24 + 8
        day_end = day_offset * 24 + 18

        if day_end >= len(times):
            return None

        dw = winds[day_start:day_end]
        dg = gusts[day_start:day_end]
        dd = dirs[day_start:day_end] if dirs else []
        dp = precip[day_start:day_end]
        dc = clouds[day_start:day_end]

        return {
            "date": times[day_start].split("T")[0],
            "avg_wind": sum(dw) / len(dw) if dw else 0,
            "max_gust": max(dg) if dg else 0,
            "wind_dir": _avg_wind_dir(dd),
            "precip_pct": sum(dp) / len(dp) if dp else 0,
            "cloud_cover": sum(dc) / len(dc) if dc else 0,
            "visibility": None,
            "ceiling": None,
        }
    except Exception:
        return None


def _metar_to_day_forecast(metar: dict) -> DayForecast:
    """Build a DayForecast from a current METAR observation."""
    wind_kt = float(metar.get("wspd") or 0)
    gust_kt = float(metar.get("wgst") or 0)
    wind_dir = None
    try:
        wdir = metar.get("wdir")
        if wdir is not None and str(wdir).upper() not in ("VRB", ""):
            wind_dir = int(float(wdir))
    except Exception:
        pass
    vis_sm = metar.get("visib")
    if vis_sm is not None:
        try:
            vis_sm = float(vis_sm)
        except Exception:
            vis_sm = None
    ceiling_ft = metar.get("ceil")
    if ceiling_ft is not None:
        try:
            ceiling_ft = int(ceiling_ft)
        except Exception:
            ceiling_ft = None

    score, issues = compute_vfr_score(
        wind_kt=wind_kt,
        gust_kt=gust_kt,
        vis_sm=vis_sm,
        ceiling_ft=ceiling_ft,
        cloud_cover_pct=0.0,
        precip_pct=0.0,
    )

    return DayForecast(
        date=datetime.now().strftime("%Y-%m-%d"),
        vfr_score=score,
        wind_kt=wind_kt,
        gust_kt=gust_kt,
        wind_dir=wind_dir,
        visibility_sm=vis_sm,
        ceiling_ft=ceiling_ft,
        precip_probability=0.0,
        cloud_cover_pct=0.0,
        confidence="high",
        source="metar",
        issues=issues,
    )


def _build_day_forecasts(
    noaa: Optional[dict],
    om: Optional[dict],
) -> list[DayForecast]:
    """Build 14 DayForecast objects (days 0-13) from available data sources."""
    forecasts = []
    today = datetime.now()

    for day_offset in range(14):
        date_str = (today + timedelta(days=day_offset)).strftime("%Y-%m-%d")
        confidence = _confidence(day_offset)

        # Days 0-7: prefer NOAA; fall back to Open-Meteo
        raw = None
        source = "open_meteo"

        if day_offset <= 7 and noaa:
            raw = _parse_noaa_day(noaa, day_offset)
            if raw:
                source = "noaa_hourly"

        if raw is None and om:
            raw = _parse_open_meteo_day(om, day_offset)

        if raw is None:
            # No data available for this day
            forecasts.append(DayForecast(
                date=date_str,
                vfr_score=50.0,
                wind_kt=0, gust_kt=0,
                wind_dir=None,
                visibility_sm=None,
                ceiling_ft=None,
                precip_probability=0,
                cloud_cover_pct=0,
                confidence=confidence,
                source=source,
                issues=["No forecast data available"],
            ))
            continue

        score, issues = compute_vfr_score(
            wind_kt=raw.get("avg_wind", 0),
            gust_kt=raw.get("max_gust", 0),
            vis_sm=raw.get("visibility"),
            ceiling_ft=raw.get("ceiling"),
            cloud_cover_pct=raw.get("cloud_cover") or 0,
            precip_pct=raw.get("precip_pct", 0),
        )

        forecasts.append(DayForecast(
            date=date_str,
            vfr_score=score,
            wind_kt=round(raw.get("avg_wind", 0), 1),
            gust_kt=round(raw.get("max_gust", 0), 1),
            wind_dir=raw.get("wind_dir"),
            visibility_sm=raw.get("visibility"),
            ceiling_ft=raw.get("ceiling"),
            precip_probability=round(raw.get("precip_pct", 0), 1),
            cloud_cover_pct=round(raw.get("cloud_cover") or 0, 1),
            confidence=confidence,
            source=source,
            issues=issues,
        ))

    return forecasts


async def get_airport_forecast(
    icao: str,
    name: str,
    lat: float,
    lon: float,
    elevation_ft: Optional[int] = None,
    distance_miles: Optional[float] = None,
    runways: Optional[list[dict]] = None,
    max_rwy_ft: Optional[int] = None,
    http_client: Optional[httpx.AsyncClient] = None,
) -> AirportForecast:
    """Fetch all weather data for one airport and return a complete AirportForecast.

    Pass ``http_client`` to reuse a shared connection pool across a fan-out
    (region / trip queries).  When omitted a short-lived client is created,
    which is fine for single-airport requests.
    """
    import time
    t0 = time.monotonic()
    _forecast_requests.add(1, {"icao": icao})
    _inflight_airports.add(1)
    try:
        async def _fetch(client: httpx.AsyncClient) -> tuple:
            metar_task = fetch_metar(client, icao)
            noaa_task = fetch_noaa_hourly(client, lat, lon)
            om_task = fetch_open_meteo(client, lat, lon)
            return await asyncio.gather(metar_task, noaa_task, om_task)

        if http_client is not None:
            metar, noaa, om = await _fetch(http_client)
        else:
            async with httpx.AsyncClient() as client:
                metar, noaa, om = await _fetch(client)
    finally:
        _inflight_airports.add(-1)

    # Current conditions from METAR
    current_metar_str = metar.get("rawOb") if metar else None
    current_day = _metar_to_day_forecast(metar) if metar else None
    current_score = current_day.vfr_score if current_day else 50.0

    # 14-day forecast
    daily = _build_day_forecasts(noaa, om)

    # Patch day 0 with METAR score if available
    if current_day and daily:
        daily[0] = current_day

    # Active AIRMETs/SIGMETs
    raw_advisories = await get_advisories_for_point(lat, lon)
    advisories = [Advisory(**a) for a in raw_advisories]

    rwy_models = [Runway(**r) for r in (runways or [])]

    _forecast_duration.record((time.monotonic() - t0) * 1000, {"icao": icao})
    return AirportForecast(
        icao=icao,
        name=name,
        lat=lat,
        lon=lon,
        elevation_ft=elevation_ft,
        distance_miles=distance_miles,
        runways=rwy_models,
        max_rwy_ft=max_rwy_ft,
        current_metar=current_metar_str,
        current_score=current_score,
        daily_forecasts=daily,
        advisories=advisories,
    )
