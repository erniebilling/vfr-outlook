import { useQuery } from '@tanstack/react-query'
import type { RegionResponse } from '../types/forecast'

async function fetchRegion(icao: string, radius: number): Promise<RegionResponse> {
  const res = await fetch(`/api/v1/region?icao=${icao}&radius=${radius}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? `Failed to fetch region for ${icao}`)
  }
  return res.json()
}

export function useRegion(icao: string | null, radius: number = 100) {
  return useQuery<RegionResponse, Error>({
    queryKey: ['region', icao, radius],
    queryFn: () => fetchRegion(icao!, radius),
    enabled: !!icao,
    staleTime: 15 * 60 * 1000,
    retry: 1,
  })
}
