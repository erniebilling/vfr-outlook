import { useQuery } from '@tanstack/react-query'
import type { AirportForecast } from '../types/forecast'

async function fetchForecast(icao: string): Promise<AirportForecast> {
  const res = await fetch(`/api/v1/airport/${icao}/forecast`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? `Failed to fetch forecast for ${icao}`)
  }
  return res.json()
}

export function useForecast(icao: string | null) {
  return useQuery<AirportForecast, Error>({
    queryKey: ['forecast', icao],
    queryFn: () => fetchForecast(icao!),
    enabled: !!icao,
    staleTime: 15 * 60 * 1000,   // 15 minutes
    retry: 1,
  })
}
