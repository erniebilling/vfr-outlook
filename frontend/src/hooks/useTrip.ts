import { useQuery } from '@tanstack/react-query'
import type { TripResponse } from '../types/forecast'

async function fetchTrip(
  origin: string,
  dest: string,
  corridorWidth: number,
  maxAirports: number,
  minRwyFt: number,
  hardSurface: boolean,
): Promise<TripResponse> {
  const params = new URLSearchParams({
    origin,
    dest,
    corridor_width: String(corridorWidth),
    max_airports: String(maxAirports),
    min_rwy_ft: String(minRwyFt),
    hard_surface: String(hardSurface),
  })
  const res = await fetch(`/api/v1/trip?${params}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? `Failed to fetch trip ${origin}→${dest}`)
  }
  return res.json()
}

export function useTrip(
  origin: string | null,
  dest: string | null,
  corridorWidth: number = 50,
  maxAirports: number = 20,
  minRwyFt: number = 2000,
  hardSurface: boolean = true,
) {
  return useQuery<TripResponse, Error>({
    queryKey: ['trip', origin, dest, corridorWidth, maxAirports, minRwyFt, hardSurface],
    queryFn: () => fetchTrip(origin!, dest!, corridorWidth, maxAirports, minRwyFt, hardSurface),
    enabled: !!origin && !!dest,
    staleTime: 15 * 60 * 1000,
    retry: 1,
  })
}
