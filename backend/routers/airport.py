from fastapi import APIRouter, HTTPException, Query
from models.forecast import AirportForecast
from services.weather import get_airport_forecast

router = APIRouter(prefix="/api/v1", tags=["airport"])


# Minimal airport lookup for Phase 1 (single airport by ICAO).
# Phase 2 will replace this with the OurAirports CSV + haversine search.
KNOWN_AIRPORTS: dict[str, dict] = {
    "KBDN": {"name": "Bend Municipal", "lat": 44.0947, "lon": -121.2005, "elevation_ft": 3460},
    "KEUG": {"name": "Eugene/Mahlon Sweet", "lat": 44.1246, "lon": -123.2119, "elevation_ft": 364},
    "KPDX": {"name": "Portland International", "lat": 45.5887, "lon": -122.5975, "elevation_ft": 31},
    "KSLE": {"name": "Salem/McNary Field", "lat": 44.9095, "lon": -123.0026, "elevation_ft": 214},
    "KOTH": {"name": "North Bend/SW Oregon Regional", "lat": 43.4171, "lon": -124.2460, "elevation_ft": 17},
    "KMFR": {"name": "Medford/Rogue Valley Intl", "lat": 42.3742, "lon": -122.8733, "elevation_ft": 1335},
    "KSMF": {"name": "Sacramento International", "lat": 38.6952, "lon": -121.5908, "elevation_ft": 27},
    "KSFO": {"name": "San Francisco International", "lat": 37.6213, "lon": -122.3790, "elevation_ft": 13},
    "KSNS": {"name": "Salinas Municipal", "lat": 36.6628, "lon": -121.6063, "elevation_ft": 85},
    "KOAK": {"name": "Oakland International", "lat": 37.7214, "lon": -122.2208, "elevation_ft": 9},
    "KSAC": {"name": "Sacramento Executive", "lat": 38.5126, "lon": -121.4924, "elevation_ft": 24},
    "KSTS": {"name": "Santa Rosa/Charles M. Schulz", "lat": 38.5089, "lon": -122.8128, "elevation_ft": 128},
    "KSBP": {"name": "San Luis Obispo County Regional", "lat": 35.2368, "lon": -120.6424, "elevation_ft": 212},
    "KSEA": {"name": "Seattle-Tacoma International", "lat": 47.4502, "lon": -122.3088, "elevation_ft": 433},
    "KRDM": {"name": "Roberts Field/Redmond", "lat": 44.2541, "lon": -121.1500, "elevation_ft": 3077},
    "KLMT": {"name": "Klamath Falls/Crater Lake", "lat": 42.1561, "lon": -121.7332, "elevation_ft": 4095},
}


@router.get("/airport/{icao}/forecast", response_model=AirportForecast)
async def airport_forecast(icao: str):
    """
    Return a 14-day VFR probability forecast for a single airport.
    """
    icao = icao.upper().strip()
    info = KNOWN_AIRPORTS.get(icao)

    if not info:
        raise HTTPException(
            status_code=404,
            detail=f"Airport '{icao}' not found. Phase 2 will add full OurAirports support.",
        )

    return await get_airport_forecast(
        icao=icao,
        name=info["name"],
        lat=info["lat"],
        lon=info["lon"],
        elevation_ft=info.get("elevation_ft"),
        distance_miles=None,
    )


@router.get("/airports/search")
async def search_airports(q: str = Query(..., min_length=2)):
    """
    Simple prefix search for Phase 1. Returns matching airport ICAO + name pairs.
    """
    q = q.upper()
    results = [
        {"icao": icao, "name": info["name"]}
        for icao, info in KNOWN_AIRPORTS.items()
        if icao.startswith(q) or q in info["name"].upper()
    ]
    return results
