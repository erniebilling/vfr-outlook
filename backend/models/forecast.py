from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime


class DayForecast(BaseModel):
    date: str                          # "2026-03-20"
    vfr_score: float                   # 0-100
    wind_kt: float
    gust_kt: float
    visibility_sm: Optional[float]
    ceiling_ft: Optional[int]
    precip_probability: float
    cloud_cover_pct: float
    confidence: Literal["high", "medium", "low"]
    source: Literal["metar", "noaa_hourly", "open_meteo"]
    issues: list[str]


class AirportForecast(BaseModel):
    icao: str
    name: str
    lat: float
    lon: float
    elevation_ft: Optional[int]
    distance_miles: Optional[float]     # None for the base airport itself
    current_metar: Optional[str]
    current_score: float
    daily_forecasts: list[DayForecast]  # 14 items


class RegionResponse(BaseModel):
    base_airport: str
    base_lat: float
    base_lon: float
    radius_miles: int
    airport_count: int
    airports: list[AirportForecast]
    generated_at: datetime
