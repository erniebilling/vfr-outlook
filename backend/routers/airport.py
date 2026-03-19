import asyncio
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from models.forecast import AirportForecast, RegionResponse
from services.weather import get_airport_forecast
from services.airports import get_airport, search_airports as db_search, airports_within_radius
from services.scorer import DEFAULT_CRITERIA

router = APIRouter(prefix="/api/v1", tags=["airport"])

_DEFAULT_RADIUS = 100  # miles
_DEFAULT_MAX_AIRPORTS = 20
_HARD_MAX_AIRPORTS = 50  # cap to keep response times reasonable


@router.get("/airport/{icao}/forecast", response_model=AirportForecast)
async def airport_forecast(icao: str):
    """14-day VFR probability forecast for a single airport."""
    icao = icao.upper().strip()
    info = get_airport(icao)
    if not info:
        raise HTTPException(status_code=404, detail=f"Airport '{icao}' not found.")

    return await get_airport_forecast(
        icao=icao,
        name=info["name"],
        lat=info["lat"],
        lon=info["lon"],
        elevation_ft=info.get("elev"),
        distance_miles=None,
        runways=info.get("runways", []),
        max_rwy_ft=info.get("max_rwy_ft"),
    )


@router.get("/region", response_model=RegionResponse)
async def region_forecast(
    icao: str = Query(..., min_length=3, max_length=4, description="Center airport ICAO"),
    radius: int = Query(_DEFAULT_RADIUS, ge=25, le=300, description="Radius in miles"),
    max_airports: int = Query(_DEFAULT_MAX_AIRPORTS, ge=1, le=_HARD_MAX_AIRPORTS, description="Maximum number of airports to return (including base)"),
    min_rwy_ft: Optional[int] = Query(None, ge=0, description="Minimum runway length in feet"),
):
    """
    Return 14-day forecasts for all airports within `radius` miles of `icao`.
    Base airport is always included as the first entry.
    """
    icao = icao.upper().strip()
    base = get_airport(icao)
    if not base:
        raise HTTPException(status_code=404, detail=f"Airport '{icao}' not found.")

    # Find nearby airports. Filter to K-prefix ICAO (US public airports with aviation wx data).
    # No max_results cap here — let the radius do the filtering, then cap after K-prefix filter.
    nearby_all = airports_within_radius(
        lat=base["lat"],
        lon=base["lon"],
        radius_miles=radius,
        max_results=10000,
        exclude_icao=icao,
        min_rwy_ft=min_rwy_ft,
    )
    nearby = [a for a in nearby_all if a["icao"].startswith("K")][:max_airports - 1]

    # Build list: base first, then nearby
    all_airports = [
        base | {"distance_miles": 0.0},
        *[a for a in nearby],
    ]

    # Fetch all forecasts concurrently
    tasks = [
        get_airport_forecast(
            icao=a["icao"],
            name=a["name"],
            lat=a["lat"],
            lon=a["lon"],
            elevation_ft=a.get("elev"),
            distance_miles=a.get("distance_miles"),
            runways=a.get("runways", []),
            max_rwy_ft=a.get("max_rwy_ft"),
        )
        for a in all_airports
    ]
    forecasts: list[AirportForecast] = await asyncio.gather(*tasks, return_exceptions=True)

    # Drop any that errored out
    valid = [f for f in forecasts if isinstance(f, AirportForecast)]

    return RegionResponse(
        base_airport=icao,
        base_lat=base["lat"],
        base_lon=base["lon"],
        radius_miles=radius,
        airport_count=len(valid),
        airports=valid,
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/airports/search")
async def search_airports(q: str = Query(..., min_length=2)):
    """Full-text search over OurAirports database. Returns ICAO + name."""
    results = db_search(q, limit=10)
    return [{"icao": a["icao"], "name": a["name"]} for a in results]


@router.get("/scoring-params")
async def scoring_params():
    """Return the current VFR scoring parameters and weights."""
    return {
        "criteria": {
            "max_wind_kt": DEFAULT_CRITERIA.max_wind_kt,
            "min_vis_sm": DEFAULT_CRITERIA.min_vis_sm,
            "min_ceiling_ft": DEFAULT_CRITERIA.min_ceiling_ft,
            "max_precip_pct": DEFAULT_CRITERIA.max_precip_pct,
        },
        "weights": {
            "wind": 0.30,
            "visibility": 0.25,
            "ceiling": 0.25,
            "precip": 0.20,
        },
        "score_thresholds": {
            "vfr": 85,
            "mvfr": 65,
            "marginal": 45,
            "poor": 25,
        },
        "scoring_ranges": {
            "wind_kt":     {"perfect": 10,   "zero": 25},
            "vis_sm":      {"perfect": 10,   "zero": 1},
            "ceiling_ft":  {"perfect": 5000, "zero": 500},
            "precip_pct":  {"perfect": 0,    "zero": 40},
        },
    }
