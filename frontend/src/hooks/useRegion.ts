import { useQuery } from '@tanstack/react-query'
import type { RegionResponse } from '../types/forecast'

async function fetchRegion(icao: string, radius: number, maxAirports: number): Promise<RegionResponse> {
  const res = await fetch(`/api/v1/region?icao=${icao}&radius=${radius}&max_airports=${maxAirports}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? `Failed to fetch region for ${icao}`)
  }
  return res.json()
}

export function useRegion(icao: string | null, radius: number = 100, maxAirports: number = 20) {
  return useQuery<RegionResponse, Error>({
    queryKey: ['region', icao, radius, maxAirports],
    queryFn: () => fetchRegion(icao!, radius, maxAirports),
    enabled: !!icao,
    staleTime: 15 * 60 * 1000,
    retry: 1,
  })
}
