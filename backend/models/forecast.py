from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime


class Advisory(BaseModel):
    type: Literal["AIRMET", "SIGMET"]
    hazard: str          # e.g. "turb-hi", "conv"
    label: str           # human-readable, e.g. "Turbulence (High)"
    severity: str        # "MOD", "SEV", "SIGMET", etc.
    altitude: str        # e.g. "FL180–FL360" or "0–16,000 ft"
    valid_until: Optional[str]   # "2230Z"
    raw: Optional[str]   # raw text for SIGMETs


class DayForecast(BaseModel):
    date: str                          # "2026-03-20"
    vfr_score: float                   # 0-100
    wind_kt: float
    gust_kt: float
    wind_dir: Optional[int]            # degrees true; None if unknown/variable
    visibility_sm: Optional[float]
    ceiling_ft: Optional[int]
    precip_probability: float
    cloud_cover_pct: float
    confidence: Literal["high", "medium", "low"]
    source: Literal["metar", "noaa_hourly", "open_meteo"]
    issues: list[str]


class Runway(BaseModel):
    le: str
    he: str
    length_ft: Optional[int]
    width_ft: Optional[int]
    surface: Optional[str]
    lighted: bool
    le_hdg: Optional[float]   # true heading of low-end
    he_hdg: Optional[float]   # true heading of high-end


class AirportForecast(BaseModel):
    icao: str
    faa: str                            # FAA / local ident (equals icao for K-prefix airports)
    name: str
    lat: float
    lon: float
    elevation_ft: Optional[int]
    distance_miles: Optional[float]     # None for the base airport itself
    runways: list[Runway] = []
    max_rwy_ft: Optional[int]
    current_metar: Optional[str]
    current_score: float
    daily_forecasts: list[DayForecast]  # 14 items
    advisories: list[Advisory] = []     # active AIRMETs/SIGMETs


class RegionResponse(BaseModel):
    base_airport: str
    base_lat: float
    base_lon: float
    radius_miles: int
    airport_count: int
    airports: list[AirportForecast]
    generated_at: datetime


class TripDayScore(BaseModel):
    date: str
    trip_score: float          # min of all corridor airports on this day
    limiting_icao: str         # airport with the worst score
    limiting_name: str
    confidence: str            # lowest confidence tier across airports


class TripResponse(BaseModel):
    origin: str
    origin_name: str
    dest: str
    dest_name: str
    corridor_miles: float
    corridor_width_miles: float
    airport_count: int
    airports: list[AirportForecast]   # corridor airports, origin first, dest last
    daily_scores: list[TripDayScore]  # 14 days, scored by worst airport
    generated_at: datetime
