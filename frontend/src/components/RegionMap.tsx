/**
 * Interactive map for the regional dashboard.
 * Uses Leaflet directly (no react-leaflet) to avoid React context issues.
 */
import { useEffect, useRef } from 'react'
import type { AirportForecast } from '../types/forecast'
import { scoreColor, scoreLabel, formatDate } from '../lib/score'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

interface Props {
  airports: AirportForecast[]
  centerLat: number
  centerLon: number
  radiusMiles: number
  dayIndex: number
  selectedIcao: string | null
  onSelect: (icao: string) => void
}

/** Miles → approximate zoom level that shows the full radius. */
function radiusToZoom(miles: number): number {
  const zoom = Math.round(Math.log2(3000 / miles)) + 5
  return Math.max(5, Math.min(12, zoom))
}

export default function RegionMap({
  airports, centerLat, centerLon, radiusMiles, dayIndex, selectedIcao, onSelect,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const markersRef = useRef<Map<string, L.CircleMarker>>(new Map())

  // Initialise map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const map = L.map(containerRef.current, {
      center: [centerLat, centerLon],
      zoom: radiusToZoom(radiusMiles),
      zoomControl: true,
    })

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
      maxZoom: 19,
    }).addTo(map)

    mapRef.current = map
    return () => {
      map.remove()
      mapRef.current = null
      markersRef.current.clear()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Recenter when airport/radius changes
  useEffect(() => {
    mapRef.current?.setView([centerLat, centerLon], radiusToZoom(radiusMiles))
  }, [centerLat, centerLon, radiusMiles])

  // Rebuild markers when airports or active day changes
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    // Remove old markers
    markersRef.current.forEach(m => m.remove())
    markersRef.current.clear()

    airports.forEach(airport => {
      const day = airport.daily_forecasts[dayIndex]
      if (!day) return

      const color = scoreColor(day.vfr_score)
      const isCenter = !airport.distance_miles
      const isSelected = airport.icao === selectedIcao

      const marker = L.circleMarker([airport.lat, airport.lon], {
        radius: isCenter ? 12 : isSelected ? 10 : 8,
        color: isSelected ? '#ffffff' : color,
        fillColor: color,
        fillOpacity: 0.9,
        weight: isSelected ? 2.5 : isCenter ? 2 : 1,
      })

      const windStr = day.wind_dir != null
        ? `${day.wind_dir}°@${day.wind_kt.toFixed(0)} kt`
        : `${day.wind_kt.toFixed(0)} kt`
      const gustStr = day.gust_kt > 0 ? ` G${day.gust_kt.toFixed(0)}` : ''
      const ceilStr = day.ceiling_ft != null ? `<tr><td style="color:#6b7280">Ceiling</td><td>${day.ceiling_ft.toLocaleString()} ft</td></tr>` : ''
      const visStr = day.visibility_sm != null ? `<tr><td style="color:#6b7280">Vis</td><td>${day.visibility_sm} sm</td></tr>` : ''
      const issuesStr = day.issues.length
        ? `<div style="margin-top:6px;padding-top:6px;border-top:1px solid #374151;color:#fb923c;font-size:11px">${day.issues.map(i => `⚠ ${i}`).join('<br>')}</div>`
        : ''

      marker.bindPopup(`
        <div style="min-width:180px;font-family:monospace;font-size:12px">
          <div style="display:flex;justify-content:space-between;margin-bottom:4px">
            <strong style="color:#60a5fa;font-size:14px">${airport.icao}</strong>
            <span style="color:#9ca3af">${formatDate(day.date)}</span>
          </div>
          <div style="color:#e5e7eb;margin-bottom:6px">${airport.name}</div>
          <table style="width:100%;border-collapse:collapse">
            <tr><td style="color:#6b7280">Score</td><td><strong style="color:${color}">${day.vfr_score.toFixed(0)} — ${scoreLabel(day.vfr_score)}</strong></td></tr>
            <tr><td style="color:#6b7280">Wind</td><td>${windStr}${gustStr}</td></tr>
            ${ceilStr}${visStr}
            <tr><td style="color:#6b7280">Precip</td><td>${day.precip_probability.toFixed(0)}%</td></tr>
          </table>
          ${issuesStr}
          <div style="margin-top:6px;color:#4b5563;font-size:11px;text-transform:capitalize">${day.confidence} confidence</div>
        </div>
      `, { maxWidth: 240 })

      marker.on('click', () => onSelect(airport.icao))
      marker.addTo(map)
      markersRef.current.set(airport.icao, marker)
    })
  }, [airports, dayIndex, selectedIcao, onSelect])

  return (
    <div
      ref={containerRef}
      className="rounded-xl overflow-hidden border border-gray-800"
      style={{ height: 400 }}
    />
  )
}
