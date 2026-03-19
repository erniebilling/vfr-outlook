import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from models.forecast import AirportForecast, RegionResponse
from services.weather import get_airport_forecast
from services.airports import get_airport, search_airports as db_search, airports_within_radius

router = APIRouter(prefix="/api/v1", tags=["airport"])

# Maximum airports fetched in a region call to keep response times reasonable
_MAX_REGION_AIRPORTS = 20
_DEFAULT_RADIUS = 100  # miles


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
    )


@router.get("/region", response_model=RegionResponse)
async def region_forecast(
    icao: str = Query(..., min_length=3, max_length=4, description="Center airport ICAO"),
    radius: int = Query(_DEFAULT_RADIUS, ge=25, le=300, description="Radius in miles"),
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
    nearby_all = airports_within_radius(
        lat=base["lat"],
        lon=base["lon"],
        radius_miles=radius,
        max_results=200,  # oversample, then filter
        exclude_icao=icao,
    )
    nearby = [a for a in nearby_all if a["icao"].startswith("K")][:_MAX_REGION_AIRPORTS - 1]

    # Build list: base first, then nearby
    all_airports = [
        {"icao": base["icao"], "name": base["name"], "lat": base["lat"],
         "lon": base["lon"], "elev": base.get("elev"), "distance_miles": 0.0},
        *[{"icao": a["icao"], "name": a["name"], "lat": a["lat"],
           "lon": a["lon"], "elev": a.get("elev"), "distance_miles": a["distance_miles"]}
          for a in nearby],
    ]

    # Fetch all forecasts concurrently
    tasks = [
        get_airport_forecast(
            icao=a["icao"],
            name=a["name"],
            lat=a["lat"],
            lon=a["lon"],
            elevation_ft=a.get("elev"),
            distance_miles=a["distance_miles"],
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
