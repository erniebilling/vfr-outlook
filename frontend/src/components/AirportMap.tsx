/**
 * Generic Leaflet map used by both RegionDashboard and TripPlanner.
 * Uses Leaflet directly (no react-leaflet) to avoid React context issues.
 *
 * Props:
 *   airports   – list of airports to render as circle markers
 *   dayIndex   – which forecast day drives marker colors
 *   fitBounds  – if provided, map fits these lat/lon bounds on load/change
 *   routeLine  – if provided, draws a dashed polyline between these points
 *   selectedIcao / onSelect – optional selection state
 */
import { useEffect, useRef } from 'react'
import type { AirportForecast } from '../types/forecast'
import { scoreColor, scoreLabel, formatDate } from '../lib/score'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

export interface LatLon { lat: number; lon: number }

interface Props {
  airports: AirportForecast[]
  dayIndex: number
  fitBounds?: [LatLon, LatLon]   // SW + NE corners, or two route endpoints
  routeLine?: LatLon[]           // draws a dashed line through these points
  selectedIcao?: string | null
  onSelect?: (icao: string) => void
  height?: number
}

function buildPopup(airport: AirportForecast, dayIndex: number): string {
  const day = airport.daily_forecasts[dayIndex]
  if (!day) return `<strong>${airport.icao}</strong>`
  const color = scoreColor(day.vfr_score)
  const windStr = day.wind_dir != null
    ? `${day.wind_dir}°@${day.wind_kt.toFixed(0)} kt`
    : `${day.wind_kt.toFixed(0)} kt`
  const gustStr = day.gust_kt > 0 ? ` G${day.gust_kt.toFixed(0)}` : ''
  const ceilStr = day.ceiling_ft != null
    ? `<tr><td style="color:#6b7280">Ceiling</td><td>${day.ceiling_ft.toLocaleString()} ft</td></tr>` : ''
  const visStr = day.visibility_sm != null
    ? `<tr><td style="color:#6b7280">Vis</td><td>${day.visibility_sm} sm</td></tr>` : ''
  const issuesStr = day.issues.length
    ? `<div style="margin-top:6px;padding-top:6px;border-top:1px solid #374151;color:#fb923c;font-size:11px">${day.issues.map(i => `⚠ ${i}`).join('<br>')}</div>`
    : ''
  return `
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
    </div>`
}

export default function AirportMap({
  airports, dayIndex, fitBounds, routeLine, selectedIcao, onSelect, height = 400,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const markersRef = useRef<Map<string, L.CircleMarker>>(new Map())
  const routeRef = useRef<L.Polyline | null>(null)

  // Initialise map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return
    const map = L.map(containerRef.current, { center: [44, -120], zoom: 6, zoomControl: true })

    const openAipKey = import.meta.env.VITE_OPENAIP_API_KEY as string | undefined

    // OSM base — always visible at all zoom levels
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map)

    // FAA VFR Sectional — overlaid at zoom 8–12
    // tileSize 512 + zoomOffset -1 requests one zoom level higher for sharper tiles
    const sectional = L.tileLayer(
      'https://tiles.arcgis.com/tiles/ssFJjBXIUyZDrSYZ/arcgis/rest/services/VFR_Sectional/MapServer/tile/{z}/{y}/{x}',
      { attribution: 'Aeronautical data &copy; FAA', maxZoom: 12 },
    )

    // OpenAIP airspace + navaid overlay — meaningful content at z7–11
    const openAip = openAipKey
      ? L.tileLayer(
          `https://api.tiles.openaip.net/api/data/openaip/{z}/{x}/{y}.png?apiKey=${openAipKey}`,
          {
            attribution: '&copy; <a href="https://www.openaip.net">OpenAIP</a>',
            minZoom: 7,
            maxZoom: 11,
            opacity: 0.9,
          },
        )
      : null

    function updateLayers() {
      const z = map.getZoom()
      if (z >= 10) {
        if (!map.hasLayer(sectional)) sectional.addTo(map)
      } else {
        if (map.hasLayer(sectional)) map.removeLayer(sectional)
      }
      if (openAip) {
        if (!map.hasLayer(openAip)) openAip.addTo(map)
      }
    }

    map.on('zoomend', updateLayers)
    updateLayers()
    mapRef.current = map
    return () => {
      map.off('zoomend', updateLayers)
      map.remove()
      mapRef.current = null
      markersRef.current.clear()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Fit bounds when route endpoints change
  useEffect(() => {
    const map = mapRef.current
    if (!map || !fitBounds) return
    const [sw, ne] = fitBounds
    map.fitBounds(
      [[Math.min(sw.lat, ne.lat), Math.min(sw.lon, ne.lon)],
       [Math.max(sw.lat, ne.lat), Math.max(sw.lon, ne.lon)]],
      { padding: [40, 40] },
    )
  }, [fitBounds])

  // Route polyline
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    routeRef.current?.remove()
    routeRef.current = null
    if (routeLine && routeLine.length >= 2) {
      routeRef.current = L.polyline(
        routeLine.map(p => [p.lat, p.lon] as L.LatLngTuple),
        { color: '#1d4ed8', weight: 2.5, opacity: 0.7, dashArray: '6 4' },
      ).addTo(map)
    }
  }, [routeLine])

  // Rebuild markers when airports, day, or selection changes
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    markersRef.current.forEach(m => m.remove())
    markersRef.current.clear()

    airports.forEach((airport, idx) => {
      const day = airport.daily_forecasts[dayIndex]
      if (!day) return
      const color = scoreColor(day.vfr_score)
      const isEndpoint = idx === 0 || idx === airports.length - 1
      const isSelected = airport.icao === selectedIcao

      const marker = L.circleMarker([airport.lat, airport.lon], {
        radius: isEndpoint ? 12 : isSelected ? 10 : 8,
        color: isSelected ? '#ffffff' : '#000000',
        fillColor: color,
        fillOpacity: 0.85,
        weight: isSelected ? 3 : isEndpoint ? 2.5 : 1.5,
      })

      marker.bindTooltip(airport.icao, {
        permanent: false,
        direction: 'top',
        offset: [0, -6],
        className: 'leaflet-vfr-tooltip',
      })
      marker.bindPopup(buildPopup(airport, dayIndex), { maxWidth: 240 })
      if (onSelect) marker.on('click', () => onSelect(airport.icao))
      marker.addTo(map)
      markersRef.current.set(airport.icao, marker)
    })
  }, [airports, dayIndex, selectedIcao, onSelect])

  return (
    <div
      ref={containerRef}
      className="rounded-xl border border-gray-800"
      style={{ height }}
    />
  )
}
