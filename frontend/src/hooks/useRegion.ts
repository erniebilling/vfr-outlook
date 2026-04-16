import { useQuery } from '@tanstack/react-query'
import type { RegionResponse } from '../types/forecast'

async function fetchRegion(icao: string, radius: number, maxAirports: number, minRwyFt: number, hardSurface: boolean): Promise<RegionResponse> {
  const params = new URLSearchParams({
    icao,
    radius: String(radius),
    max_airports: String(maxAirports),
    min_rwy_ft: String(minRwyFt),
    hard_surface: String(hardSurface),
  })
  const res = await fetch(`/api/v1/region?${params}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? `Failed to fetch region for ${icao}`)
  }
  return res.json()
}

export function useRegion(icao: string | null, radius: number = 100, maxAirports: number = 20, minRwyFt: number = 2000, hardSurface: boolean = true) {
  return useQuery<RegionResponse, Error>({
    queryKey: ['region', icao, radius, maxAirports, minRwyFt, hardSurface],
    queryFn: () => fetchRegion(icao!, radius, maxAirports, minRwyFt, hardSurface),
    enabled: !!icao,
    staleTime: 15 * 60 * 1000,
    retry: 1,
  })
}
