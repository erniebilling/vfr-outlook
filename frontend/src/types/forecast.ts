export type Confidence = 'high' | 'medium' | 'low'
export type ForecastSource = 'metar' | 'noaa_hourly' | 'open_meteo'

export interface Advisory {
  type: 'AIRMET' | 'SIGMET'
  hazard: string
  label: string
  severity: string
  altitude: string
  valid_until: string | null
  raw: string | null
}

export interface DayForecast {
  date: string
  vfr_score: number
  wind_kt: number
  gust_kt: number
  visibility_sm: number | null
  ceiling_ft: number | null
  precip_probability: number
  cloud_cover_pct: number
  confidence: Confidence
  source: ForecastSource
  issues: string[]
}

export interface AirportForecast {
  icao: string
  name: string
  lat: number
  lon: number
  elevation_ft: number | null
  distance_miles: number | null
  current_metar: string | null
  current_score: number
  daily_forecasts: DayForecast[]
  advisories: Advisory[]
}

export interface RegionResponse {
  base_airport: string
  base_lat: number
  base_lon: number
  radius_miles: number
  airport_count: number
  airports: AirportForecast[]
  generated_at: string
}
