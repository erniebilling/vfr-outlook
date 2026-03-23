import { useMemo } from 'react'
import type { AirportForecast } from '../types/forecast'
import AirportMap from './AirportMap'

interface Props {
  airports: AirportForecast[]
  centerLat: number
  centerLon: number
  radiusMiles: number
  dayIndex: number
  selectedIcao: string | null
  onSelect: (icao: string) => void
}

export default function RegionMap({ airports, centerLat, centerLon, radiusMiles, dayIndex, selectedIcao, onSelect }: Props) {
  // Pad the bounds by the radius so the circle fits
  const degPad = radiusMiles / 69
  const fitBounds = useMemo(() => ([
    { lat: centerLat - degPad, lon: centerLon - degPad },
    { lat: centerLat + degPad, lon: centerLon + degPad },
  ] as [{ lat: number; lon: number }, { lat: number; lon: number }]),
  [centerLat, centerLon, degPad])

  return (
    <AirportMap
      airports={airports}
      dayIndex={dayIndex}
      fitBounds={fitBounds}
      selectedIcao={selectedIcao}
      onSelect={onSelect}
    />
  )
}
