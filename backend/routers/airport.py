import asyncio
import math
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request
from models.forecast import AirportForecast, RegionResponse, TripResponse, TripDayScore
from services.weather import get_airport_forecast
from services.airports import get_airport, search_airports as db_search, airports_within_radius, airports_in_corridor, _haversine_miles
from services.scorer import DEFAULT_CRITERIA
from otel import get_tracer, get_meter

router = APIRouter(prefix="/api/v1", tags=["airport"])

_tracer = get_tracer("vfr-outlook.routers.airport")
_meter = get_meter("vfr-outlook.routers.airport")

# ── Metrics instruments ───────────────────────────────────────────────────────
_region_requests = _meter.create_counter(
    "vfr.region.requests",
    description="Total number of region forecast requests",
    unit="1",
)
_trip_requests = _meter.create_counter(
    "vfr.trip.requests",
    description="Total number of trip forecast requests",
    unit="1",
)
_region_airports_returned = _meter.create_histogram(
    "vfr.region.airports_returned",
    description="Number of airports returned per region request",
    unit="1",
)

_DEFAULT_RADIUS = 100  # miles
_DEFAULT_MAX_AIRPORTS = 20
_HARD_MAX_AIRPORTS = 50  # cap to keep response times reasonable


@router.get("/airport/{icao}/forecast", response_model=AirportForecast)
async def airport_forecast(icao: str):
    """14-day VFR probability forecast for a single airport."""
    icao = icao.upper().strip()

    with _tracer.start_as_current_span("airport_forecast") as span:
        span.set_attribute("airport.icao", icao)
        info = get_airport(icao)
        if not info:
            span.set_attribute("error", True)
            raise HTTPException(status_code=404, detail=f"Airport '{icao}' not found.")

        span.set_attribute("airport.name", info["name"])
        span.set_attribute("airport.lat", info["lat"])
        span.set_attribute("airport.lon", info["lon"])

        result = await get_airport_forecast(
            icao=icao,
            name=info["name"],
            lat=info["lat"],
            lon=info["lon"],
            elevation_ft=info.get("elev"),
            distance_miles=None,
            runways=info.get("runways", []),
            max_rwy_ft=info.get("max_rwy_ft"),
        )
        return result


@router.get("/region", response_model=RegionResponse)
async def region_forecast(
    request: Request,
    icao: str = Query(..., min_length=3, max_length=4, description="Center airport ICAO"),
    radius: int = Query(_DEFAULT_RADIUS, ge=25, le=300, description="Radius in miles"),
    max_airports: int = Query(_DEFAULT_MAX_AIRPORTS, ge=1, le=_HARD_MAX_AIRPORTS, description="Maximum number of airports to return (including base)"),
    min_rwy_ft: Optional[int] = Query(None, ge=0, description="Minimum runway length in feet"),
    hard_surface: bool = Query(True, description="Only include airports with hard surface runways"),
):
    """
    Return 14-day forecasts for all airports within `radius` miles of `icao`.
    Base airport is always included as the first entry.
    """
    icao = icao.upper().strip()
    _region_requests.add(1, {"icao": icao, "radius_miles": str(radius)})

    with _tracer.start_as_current_span("region_forecast") as span:
        span.set_attribute("airport.icao", icao)
        span.set_attribute("region.radius_miles", radius)
        span.set_attribute("region.max_airports", max_airports)

        base = get_airport(icao)
        if not base:
            span.set_attribute("error", True)
            raise HTTPException(status_code=404, detail=f"Airport '{icao}' not found.")

        # Find nearby airports. No max_results cap here — let the radius do the filtering,
        # then cap after. We intentionally include non-K airports (e.g. S39, 7S5) because
        # the weather stack uses lat/lon for forecasts and handles missing METARs gracefully.
        nearby_all = airports_within_radius(
            lat=base["lat"],
            lon=base["lon"],
            radius_miles=radius,
            max_results=10000,
            exclude_icao=icao,
            min_rwy_ft=min_rwy_ft,
            hard_surface=hard_surface,
        )
        nearby = nearby_all[:max_airports - 1]

        # Build list: base first, then nearby
        all_airports = [
            base | {"distance_miles": 0.0},
            *[a for a in nearby],
        ]

        # Fetch all forecasts concurrently, sharing the app-level HTTP client
        # so all airports reuse the same connection pool.
        http_client = getattr(request.app.state, "http_client", None)
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
                http_client=http_client,
            )
            for a in all_airports
        ]
        forecasts = await asyncio.gather(*tasks, return_exceptions=True)

        # Drop any that errored out
        valid = [f for f in forecasts if isinstance(f, AirportForecast)]

        span.set_attribute("region.airports_returned", len(valid))
        _region_airports_returned.record(len(valid), {"icao": icao, "radius_miles": str(radius)})

        return RegionResponse(
            base_airport=icao,
            base_lat=base["lat"],
            base_lon=base["lon"],
            radius_miles=radius,
            airport_count=len(valid),
            airports=valid,
            generated_at=datetime.now(timezone.utc),
        )


_CONFIDENCE_ORDER = {"high": 0, "medium": 1, "low": 2}


@router.get("/trip", response_model=TripResponse)
async def trip_forecast(
    request: Request,
    origin: str = Query(..., min_length=2, max_length=5),
    dest: str = Query(..., min_length=2, max_length=5),
    corridor_width: int = Query(50, ge=10, le=150, description="Corridor half-width in miles"),
    max_airports: int = Query(20, ge=2, le=50),
    min_rwy_ft: Optional[int] = Query(None, ge=0),
    hard_surface: bool = Query(True, description="Only include airports with hard surface runways"),
):
    """
    Return 14-day trip forecasts for airports along the corridor between origin and dest.
    Per-day trip score = worst (min) VFR score across all corridor airports.
    """
    origin = origin.upper().strip()
    dest = dest.upper().strip()
    _trip_requests.add(1, {"origin": origin, "dest": dest})

    with _tracer.start_as_current_span("trip_forecast") as span:
        span.set_attribute("trip.origin", origin)
        span.set_attribute("trip.dest", dest)
        span.set_attribute("trip.corridor_width_miles", corridor_width)

        orig_info = get_airport(origin)
        dest_info = get_airport(dest)
        if not orig_info:
            span.set_attribute("error", True)
            raise HTTPException(status_code=404, detail=f"Origin airport '{origin}' not found.")
        if not dest_info:
            span.set_attribute("error", True)
            raise HTTPException(status_code=404, detail=f"Destination airport '{dest}' not found.")

        corridor_miles = _haversine_miles(
            orig_info["lat"], orig_info["lon"],
            dest_info["lat"], dest_info["lon"],
        )
        span.set_attribute("trip.corridor_miles", round(corridor_miles, 1))

        # Find corridor airports (excluding origin/dest — added separately)
        corridor = airports_in_corridor(
            lat1=orig_info["lat"], lon1=orig_info["lon"],
            lat2=dest_info["lat"], lon2=dest_info["lon"],
            width_miles=corridor_width,
            exclude_icaos=(origin, dest),
            min_rwy_ft=min_rwy_ft,
            hard_surface=hard_surface,
        )
        # Evenly space corridor airports rather than taking the first N (which clusters near origin).
        # Include non-K airports (e.g. S39, 7S5) — weather stack uses lat/lon and handles
        # missing METARs gracefully.
        corridor_airports_all = corridor
        n_slots = max_airports - 2  # slots between origin and dest
        if len(corridor_airports_all) <= n_slots:
            k_airports = corridor_airports_all
        else:
            # airports_in_corridor returns them sorted by along-track t ∈ [0,1].
            # Assign each airport a t value by its index position, then pick one
            # per evenly-spaced bucket.
            total = len(corridor_airports_all)
            bucket_size = total / n_slots
            k_airports = []
            for slot in range(n_slots):
                # target index = midpoint of this bucket
                target = (slot + 0.5) * bucket_size
                idx = min(round(target), total - 1)
                k_airports.append(corridor_airports_all[idx])

        all_airports = [
            orig_info | {"cross_track_miles": 0.0},
            *k_airports,
            dest_info | {"cross_track_miles": 0.0},
        ]

        # Fetch forecasts concurrently, sharing the app-level HTTP client.
        http_client = getattr(request.app.state, "http_client", None)
        tasks = [
            get_airport_forecast(
                icao=a["icao"],
                name=a["name"],
                lat=a["lat"],
                lon=a["lon"],
                elevation_ft=a.get("elev"),
                distance_miles=a.get("cross_track_miles"),
                runways=a.get("runways", []),
                max_rwy_ft=a.get("max_rwy_ft"),
                http_client=http_client,
            )
            for a in all_airports
        ]
        forecasts = [
            f for f in await asyncio.gather(*tasks, return_exceptions=True)
            if isinstance(f, AirportForecast)
        ]
        span.set_attribute("trip.airports_fetched", len(forecasts))

        # Build per-day trip scores (worst airport wins)
        num_days = max(len(f.daily_forecasts) for f in forecasts) if forecasts else 0
        daily_scores: list[TripDayScore] = []
        for i in range(num_days):
            day_scores = [
                (f.daily_forecasts[i].vfr_score, f.icao, f.name, f.daily_forecasts[i].confidence)
                for f in forecasts
                if i < len(f.daily_forecasts)
            ]
            if not day_scores:
                continue
            worst_score, worst_icao, worst_name, _ = min(day_scores, key=lambda x: x[0])
            worst_conf = max(
                (conf for _, _, _, conf in day_scores),
                key=lambda c: _CONFIDENCE_ORDER.get(c, 99),
            )
            daily_scores.append(TripDayScore(
                date=forecasts[0].daily_forecasts[i].date,
                trip_score=worst_score,
                limiting_icao=worst_icao,
                limiting_name=worst_name,
                confidence=worst_conf,
            ))

        return TripResponse(
            origin=origin,
            origin_name=orig_info["name"],
            dest=dest,
            dest_name=dest_info["name"],
            corridor_miles=round(corridor_miles, 1),
            corridor_width_miles=float(corridor_width),
            airport_count=len(forecasts),
            airports=forecasts,
            daily_scores=daily_scores,
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
