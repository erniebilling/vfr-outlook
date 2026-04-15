"""
Fetch active AIRMETs and SIGMETs from aviationweather.gov and filter
them to those whose polygons contain (or are near) a given lat/lon point.

Hazards covered:
  G-AIRMET TANGO  — turb-hi, turb-lo, llws (low-level wind shear)
  SIGMET          — conv, turb
"""

import asyncio
import logging
import time
import httpx
from datetime import datetime, timezone
from typing import Optional

from otel import get_meter

AWWS_BASE = "https://aviationweather.gov/api/data"

_log = logging.getLogger(__name__)

_meter = get_meter("vfr-outlook.services.advisories")
_advisory_fetch_errors = _meter.create_counter(
    "vfr.advisory.fetch_errors",
    description="Number of failed fetches to the Aviation Weather advisory endpoints",
    unit="1",
)

# ---------------------------------------------------------------------------
# In-process advisory cache — G-AIRMETs update at most every 3 hours, so
# a 5-minute TTL means at worst one fetch per 5 minutes regardless of how
# many airports are in a region/trip request.
# ---------------------------------------------------------------------------
_ADVISORY_CACHE_TTL_S = 300  # 5 minutes

_cached_gairmets: list[dict] = []
_cached_sigmets:  list[dict] = []
_cache_fetched_at: float = 0.0   # epoch seconds; 0 means never fetched
_cache_lock = asyncio.Lock()

# G-AIRMET hazards we care about (TANGO product = turbulence/wind)
_GAIRMET_HAZARDS = ["turb-hi", "turb-lo", "llws"]

# SIGMET hazards we care about
_SIGMET_HAZARDS = ["conv", "turb"]

_HAZARD_LABELS = {
    "turb-hi": "Turbulence (High)",
    "turb-lo": "Turbulence (Low)",
    "llws":    "Low-Level Wind Shear",
    "conv":    "Convective",
    "turb":    "Turbulence",
}

_HAZARD_SEVERITY = {
    "conv":    "SIGMET",
    "turb":    "SIGMET",
    "turb-hi": "AIRMET",
    "turb-lo": "AIRMET",
    "llws":    "AIRMET",
}


def _point_in_polygon(lat: float, lon: float, coords: list[dict]) -> bool:
    """Ray-casting point-in-polygon test."""
    if len(coords) < 3:
        return False
    inside = False
    n = len(coords)
    j = n - 1
    for i in range(n):
        try:
            xi, yi = float(coords[i]["lon"]), float(coords[i]["lat"])
            xj, yj = float(coords[j]["lon"]), float(coords[j]["lat"])
        except (TypeError, ValueError):
            j = i
            continue
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _near_polyline(lat: float, lon: float, coords: list[dict], threshold_deg: float = 1.5) -> bool:
    """Check if point is within threshold_deg of any segment of a LINE geometry."""
    for c in coords:
        try:
            if abs(float(c["lat"]) - lat) < threshold_deg and abs(float(c["lon"]) - lon) < threshold_deg:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _is_relevant(lat: float, lon: float, item: dict, geometry_type: Optional[str] = None) -> bool:
    coords = item.get("coords", [])
    if not coords:
        return False
    geom = (geometry_type or item.get("geometryType") or item.get("geom") or "AREA").upper()
    if geom == "LINE":
        return _near_polyline(lat, lon, coords)
    return _point_in_polygon(lat, lon, coords)


async def _fetch_gairmets(client: httpx.AsyncClient) -> list[dict]:
    """Fetch all active G-AIRMETs for our hazard types."""
    results = []
    tasks = [
        client.get(
            f"{AWWS_BASE}/gairmet",
            params={"hazard": h, "format": "json"},
            timeout=10,
        )
        for h in _GAIRMET_HAZARDS
    ]
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    for h, resp in zip(_GAIRMET_HAZARDS, responses):
        if isinstance(resp, Exception):
            _log.warning("G-AIRMET fetch failed for hazard=%s: %s", h, resp)
            _advisory_fetch_errors.add(1, {"endpoint": "gairmet", "hazard": h})
            continue
        try:
            resp.raise_for_status()
            for item in resp.json():
                item["_hazard_key"] = h
            results.extend(resp.json())
        except Exception as exc:
            _log.warning("G-AIRMET parse/HTTP error for hazard=%s: %s", h, exc)
            _advisory_fetch_errors.add(1, {"endpoint": "gairmet", "hazard": h})
    return results


async def _fetch_sigmets(client: httpx.AsyncClient) -> list[dict]:
    """Fetch all active SIGMETs for our hazard types."""
    results = []
    tasks = [
        client.get(
            f"{AWWS_BASE}/airsigmet",
            params={"hazard": h, "format": "json"},
            timeout=10,
        )
        for h in _SIGMET_HAZARDS
    ]
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    for h, resp in zip(_SIGMET_HAZARDS, responses):
        if isinstance(resp, Exception):
            _log.warning("SIGMET fetch failed for hazard=%s: %s", h, resp)
            _advisory_fetch_errors.add(1, {"endpoint": "airsigmet", "hazard": h})
            continue
        try:
            resp.raise_for_status()
            for item in resp.json():
                item["_hazard_key"] = h
            results.extend(resp.json())
        except Exception as exc:
            _log.warning("SIGMET parse/HTTP error for hazard=%s: %s", h, exc)
            _advisory_fetch_errors.add(1, {"endpoint": "airsigmet", "hazard": h})
    return results


def _format_gairmet(item: dict) -> dict:
    h = item.get("_hazard_key", "")
    valid_time = item.get("validTime", "")
    expire_ts = item.get("expireTime")
    expire_str = None
    if expire_ts:
        try:
            expire_str = datetime.fromtimestamp(expire_ts, tz=timezone.utc).strftime("%H%MZ")
        except Exception:
            pass

    base = item.get("base")
    top = item.get("top")
    alt = ""
    if base is not None and top is not None:
        alt = f"FL{base}–FL{top}"
    elif top is not None:
        alt = f"below FL{top}"

    return {
        "type": "AIRMET",
        "hazard": h,
        "label": _HAZARD_LABELS.get(h, h.upper()),
        "severity": item.get("severity") or "MOD",
        "altitude": alt,
        "valid_until": expire_str,
        "raw": None,
    }


def _format_sigmet(item: dict) -> dict:
    h = item.get("_hazard_key", "")
    expire_ts = item.get("validTimeTo")
    expire_str = None
    if expire_ts:
        try:
            expire_str = datetime.fromtimestamp(expire_ts, tz=timezone.utc).strftime("%H%MZ")
        except Exception:
            pass

    lo1 = item.get("altitudeLow1")
    hi2 = item.get("altitudeHi2")
    alt = ""
    if lo1 is not None and hi2 is not None:
        alt = f"{lo1:,}–{hi2:,} ft"
    elif hi2 is not None:
        alt = f"below {hi2:,} ft"

    sev = item.get("severity")
    sev_label = ""
    if sev == 5:
        sev_label = "SEV"
    elif sev == 3:
        sev_label = "MOD"

    return {
        "type": "SIGMET",
        "hazard": h,
        "label": _HAZARD_LABELS.get(h, h.upper()),
        "severity": sev_label or "MOD",
        "altitude": alt,
        "valid_until": expire_str,
        "raw": item.get("rawAirSigmet"),
    }


async def _refresh_cache_if_needed() -> None:
    """Fetch fresh advisory data if the cache is stale, holding a lock so
    concurrent callers within the same process only trigger one fetch.

    On failure the stale cache is kept (advisories degrade gracefully to
    empty) and _cache_fetched_at is still advanced so a broken upstream
    doesn't trigger a new fetch — and new timeout delays — on every request.
    """
    global _cached_gairmets, _cached_sigmets, _cache_fetched_at
    if time.monotonic() - _cache_fetched_at < _ADVISORY_CACHE_TTL_S:
        return
    async with _cache_lock:
        # Re-check inside the lock — another coroutine may have refreshed
        # while we were waiting.
        if time.monotonic() - _cache_fetched_at < _ADVISORY_CACHE_TTL_S:
            return
        try:
            async with httpx.AsyncClient() as client:
                gairmets, sigmets = await asyncio.gather(
                    _fetch_gairmets(client),
                    _fetch_sigmets(client),
                )
            _cached_gairmets = gairmets
            _cached_sigmets = sigmets
        except Exception as exc:
            _log.error("Advisory cache refresh failed, keeping stale data: %s", exc)
        finally:
            # Always advance the timestamp so a broken upstream doesn't
            # cause a thundering herd of timeout-delay fetches.
            _cache_fetched_at = time.monotonic()


async def get_advisories_for_point(lat: float, lon: float) -> list[dict]:
    """
    Return a list of active AIRMET/SIGMET advisories whose polygon
    contains the given lat/lon point.  Advisory data is fetched once and
    cached for up to _ADVISORY_CACHE_TTL_S seconds.
    """
    await _refresh_cache_if_needed()
    gairmets = _cached_gairmets
    sigmets  = _cached_sigmets

    advisories = []

    for item in gairmets:
        if _is_relevant(lat, lon, item):
            advisories.append(_format_gairmet(item))

    for item in sigmets:
        if _is_relevant(lat, lon, item):
            advisories.append(_format_sigmet(item))

    # Deduplicate by (type, hazard, altitude)
    seen = set()
    unique = []
    for a in advisories:
        key = (a["type"], a["hazard"], a["altitude"])
        if key not in seen:
            seen.add(key)
            unique.append(a)

    return unique
