export type Confidence = 'high' | 'medium' | 'low'
export type ForecastSource = 'metar' | 'noaa_hourly' | 'open_meteo'

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
}
