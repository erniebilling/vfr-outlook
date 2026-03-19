"""
Airport database loaded from data/airports_us.json (OurAirports).
Provides fast haversine radius search.
"""

import json
import math
from pathlib import Path
from functools import lru_cache
from typing import Optional

_DATA_PATH = Path(__file__).parent.parent / "data" / "airports_us.json"


@lru_cache(maxsize=1)
def _load() -> list[dict]:
    with open(_DATA_PATH) as f:
        return json.load(f)


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 3958.8  # Earth radius in miles
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def get_airport(icao: str) -> Optional[dict]:
    icao = icao.upper()
    for ap in _load():
        if ap["icao"] == icao:
            return ap
    return None


def search_airports(query: str, limit: int = 10) -> list[dict]:
    q = query.upper()
    icao_matches = []
    name_matches = []
    for ap in _load():
        if q in ap["icao"]:
            icao_matches.append(ap)
        elif q in ap["name"].upper():
            name_matches.append(ap)
    combined = icao_matches + name_matches
    return combined[:limit]


def airports_within_radius(
    lat: float,
    lon: float,
    radius_miles: float,
    max_results: int = 20,
    exclude_icao: Optional[str] = None,
    types: tuple[str, ...] = ("small_airport", "medium_airport", "large_airport"),
    min_rwy_ft: Optional[int] = None,
) -> list[dict]:
    """Return airports within radius_miles, sorted by distance, capped at max_results."""
    nearby = []
    for ap in _load():
        if ap.get("type") not in types:
            continue
        if exclude_icao and ap["icao"] == exclude_icao.upper():
            continue
        if min_rwy_ft is not None:
            max_rwy = ap.get("max_rwy_ft")
            if max_rwy is None or max_rwy < min_rwy_ft:
                continue
        dist = _haversine_miles(lat, lon, ap["lat"], ap["lon"])
        if dist <= radius_miles:
            nearby.append({**ap, "distance_miles": round(dist, 1)})
    nearby.sort(key=lambda x: x["distance_miles"])
    return nearby[:max_results]
