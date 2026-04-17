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


def get_airport(code: str) -> Optional[dict]:
    """Look up an airport by ICAO code, FAA ident, or METAR station ID."""
    code = code.upper()
    for ap in _load():
        if ap["icao"] == code or ap.get("faa") == code or ap.get("metar_id") == code:
            return ap
    return None


def search_airports(query: str, limit: int = 10) -> list[dict]:
    q = query.upper()
    code_matches = []
    name_matches = []
    for ap in _load():
        if q in ap["icao"] or q in ap.get("faa", ""):
            code_matches.append(ap)
        elif q in ap["name"].upper():
            name_matches.append(ap)
    combined = code_matches + name_matches
    return combined[:limit]


def _point_to_segment_dist_miles(
    lat: float, lon: float,
    lat1: float, lon1: float,
    lat2: float, lon2: float,
) -> float:
    """
    Approximate cross-track / along-track distance from a point to a great-circle segment.
    Uses flat-earth approximation (fine for corridors < 500 mi).
    Returns distance in miles from the point to the nearest point on the segment.
    """
    # Convert to rough x/y in miles (equirectangular)
    R = 3958.8
    mid_lat = math.radians((lat1 + lat2) / 2)
    cos_lat = math.cos(mid_lat)

    ax = math.radians(lon1) * cos_lat * R
    ay = math.radians(lat1) * R
    bx = math.radians(lon2) * cos_lat * R
    by = math.radians(lat2) * R
    px = math.radians(lon) * cos_lat * R
    py = math.radians(lat) * R

    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    ab_len_sq = abx * abx + aby * aby
    if ab_len_sq == 0:
        return math.hypot(apx, apy)
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / ab_len_sq))
    closest_x = ax + t * abx
    closest_y = ay + t * aby
    return math.hypot(px - closest_x, py - closest_y)


def airports_in_corridor(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    width_miles: float = 50.0,
    exclude_icaos: tuple[str, ...] = (),
    min_rwy_ft: Optional[int] = None,
    hard_surface: bool = True,
) -> list[dict]:
    """
    Return airports within `width_miles` of the great-circle path between two points,
    sorted by along-track position (origin → dest order).
    """
    exclude = {i.upper() for i in exclude_icaos}
    results = []
    for ap in _load():
        if ap.get("type") not in ("small_airport", "medium_airport", "large_airport"):
            continue
        if ap["icao"] in exclude:
            continue
        if min_rwy_ft is not None:
            max_rwy = ap.get("max_rwy_ft")
            if max_rwy is None or max_rwy < min_rwy_ft:
                continue
        if hard_surface and not ap.get("has_hard_surface"):
            continue
        dist = _point_to_segment_dist_miles(ap["lat"], ap["lon"], lat1, lon1, lat2, lon2)
        if dist <= width_miles:
            results.append({**ap, "cross_track_miles": round(dist, 1)})

    # Sort by along-track position (project onto origin→dest axis)
    R = 3958.8
    mid_lat = math.radians((lat1 + lat2) / 2)
    cos_lat = math.cos(mid_lat)
    ax = math.radians(lon1) * cos_lat * R
    ay = math.radians(lat1) * R
    bx = math.radians(lon2) * cos_lat * R
    by = math.radians(lat2) * R
    abx, aby = bx - ax, by - ay

    def along_track(ap: dict) -> float:
        px = math.radians(ap["lon"]) * cos_lat * R
        py = math.radians(ap["lat"]) * R
        ab_len_sq = abx * abx + aby * aby
        if ab_len_sq == 0:
            return 0.0
        return ((px - ax) * abx + (py - ay) * aby) / ab_len_sq

    results.sort(key=along_track)
    return results


def airports_within_radius(
    lat: float,
    lon: float,
    radius_miles: float,
    max_results: int = 20,
    exclude_icao: Optional[str] = None,
    types: tuple[str, ...] = ("small_airport", "medium_airport", "large_airport"),
    min_rwy_ft: Optional[int] = None,
    hard_surface: bool = True,
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
        if hard_surface and not ap.get("has_hard_surface"):
            continue
        dist = _haversine_miles(lat, lon, ap["lat"], ap["lon"])
        if dist <= radius_miles:
            nearby.append({**ap, "distance_miles": round(dist, 1)})
    nearby.sort(key=lambda x: x["distance_miles"])
    return nearby[:max_results]
