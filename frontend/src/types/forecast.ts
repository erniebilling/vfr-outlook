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
  wind_dir: number | null
  visibility_sm: number | null
  ceiling_ft: number | null
  precip_probability: number
  cloud_cover_pct: number
  confidence: Confidence
  source: ForecastSource
  issues: string[]
}

export interface Runway {
  le: string
  he: string
  length_ft: number | null
  width_ft: number | null
  surface: string | null
  lighted: boolean
  le_hdg: number | null
  he_hdg: number | null
}

export interface AirportForecast {
  icao: string
  name: string
  lat: number
  lon: number
  elevation_ft: number | null
  distance_miles: number | null
  runways: Runway[]
  max_rwy_ft: number | null
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

export interface TripDayScore {
  date: string
  trip_score: number
  limiting_icao: string
  limiting_name: string
  confidence: string
}

export interface TripResponse {
  origin: string
  origin_name: string
  dest: string
  dest_name: string
  corridor_miles: number
  corridor_width_miles: number
  airport_count: number
  airports: AirportForecast[]
  daily_scores: TripDayScore[]
  generated_at: string
}
