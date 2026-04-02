"""
Weather data fetching service.
Aggregates METAR (current), NOAA hourly (days 0-7), and Open-Meteo (days 0-16).
"""

import asyncio
import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional

from models.forecast import DayForecast, AirportForecast, Advisory, Runway
from services.scorer import compute_vfr_score
from services.advisories import get_advisories_for_point


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
    try:
        resp = await client.get(
            f"{AVIATION_WEATHER_BASE}/metar",
            params={"ids": icao, "format": "json", "taf": "false", "hours": "2"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return data[0] if data else None
    except Exception:
        return None


async def fetch_noaa_hourly(client: httpx.AsyncClient, lat: float, lon: float) -> Optional[dict]:
    try:
        points_resp = await client.get(
            f"{NOAA_POINTS_BASE}/{lat:.4f},{lon:.4f}",
            headers=NOAA_HEADERS,
            timeout=10,
        )
        points_resp.raise_for_status()
        forecast_url = points_resp.json()["properties"]["forecastHourly"]

        hourly_resp = await client.get(forecast_url, headers=NOAA_HEADERS, timeout=15)
        hourly_resp.raise_for_status()
        return hourly_resp.json()
    except Exception:
        return None


async def fetch_open_meteo(client: httpx.AsyncClient, lat: float, lon: float) -> Optional[dict]:
    try:
        resp = await client.get(
            OPEN_METEO_BASE,
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "precipitation_probability,windspeed_10m,windgusts_10m,winddirection_10m,cloudcover",
                "forecast_days": 16,
                "windspeed_unit": "kn",
                "precipitation_unit": "inch",
                "timezone": "America/Los_Angeles",
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


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
) -> AirportForecast:
    """Fetch all weather data for one airport and return a complete AirportForecast."""
    async with httpx.AsyncClient() as client:
        metar_task = fetch_metar(client, icao)
        noaa_task = fetch_noaa_hourly(client, lat, lon)
        om_task = fetch_open_meteo(client, lat, lon)

        metar, noaa, om = await asyncio.gather(metar_task, noaa_task, om_task)

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
