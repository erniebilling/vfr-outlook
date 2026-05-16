import { useQuery } from '@tanstack/react-query'
import type { RegionResponse } from '../types/forecast'

interface NearbyParams {
  lat: number
  lon: number
  radius: number
  maxAirports: number
  minRwyFt: number
  hardSurface: boolean
}

async function fetchNearby(p: NearbyParams): Promise<RegionResponse> {
  const params = new URLSearchParams({
    lat: String(p.lat),
    lon: String(p.lon),
    radius: String(p.radius),
    max_airports: String(p.maxAirports),
    min_rwy_ft: String(p.minRwyFt),
    hard_surface: String(p.hardSurface),
  })
  const res = await fetch(`/api/v1/region/nearby?${params}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? 'Failed to fetch nearby airports')
  }
  return res.json()
}

export function useNearby(params: NearbyParams | null) {
  return useQuery<RegionResponse, Error>({
    queryKey: ['nearby', params],
    queryFn: () => fetchNearby(params!),
    enabled: params !== null,
    staleTime: 15 * 60 * 1000,
    retry: 1,
  })
}
