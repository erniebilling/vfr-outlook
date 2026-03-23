/**
 * Interactive map for the regional dashboard.
 * Uses Leaflet + react-leaflet with OpenStreetMap tiles.
 * Airports render as circle markers colored by their VFR score for the
 * currently-selected forecast day.
 */
import { useEffect } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet'
import type { AirportForecast } from '../types/forecast'
import { scoreColor, scoreLabel, formatDate } from '../lib/score'
import 'leaflet/dist/leaflet.css'

// Recenter + rezoom whenever the center airport or radius changes.
function MapController({ lat, lon, radiusMiles }: { lat: number; lon: number; radiusMiles: number }) {
  const map = useMap()
  useEffect(() => {
    // Pick a zoom level that shows roughly the full radius circle.
    // ~69 miles per degree latitude; we want the radius to fill ~40% of viewport.
    const deg = radiusMiles / 69
    const zoom = Math.round(Math.log2(360 / (deg * 4))) + 1
    const clamped = Math.max(5, Math.min(12, zoom))
    map.setView([lat, lon], clamped)
  }, [lat, lon, radiusMiles, map])
  return null
}

interface Props {
  airports: AirportForecast[]
  centerLat: number
  centerLon: number
  radiusMiles: number
  dayIndex: number                        // which forecast day to color by
  selectedIcao: string | null
  onSelect: (icao: string) => void
}

export default function RegionMap({
  airports,
  centerLat,
  centerLon,
  radiusMiles,
  dayIndex,
  selectedIcao,
  onSelect,
}: Props) {
  return (
    <div className="rounded-xl overflow-hidden border border-gray-800" style={{ height: 400 }}>
      <MapContainer
        center={[centerLat, centerLon]}
        zoom={8}
        style={{ height: '100%', width: '100%', background: '#0f172a' }}
        zoomControl={true}
        scrollWheelZoom={true}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        />
        <MapController lat={centerLat} lon={centerLon} radiusMiles={radiusMiles} />

        {airports.map(airport => {
          const day = airport.daily_forecasts[dayIndex]
          if (!day) return null
          const color = scoreColor(day.vfr_score)
          const isCenter = airport.distance_miles === 0 || airport.distance_miles == null
          const isSelected = airport.icao === selectedIcao

          return (
            <CircleMarker
              key={airport.icao}
              center={[airport.lat, airport.lon]}
              radius={isCenter ? 12 : isSelected ? 10 : 8}
              pathOptions={{
                color: isSelected ? '#ffffff' : color,
                fillColor: color,
                fillOpacity: 0.9,
                weight: isSelected ? 2.5 : isCenter ? 2 : 1,
              }}
              eventHandlers={{ click: () => onSelect(airport.icao) }}
            >
              <Popup>
                <div style={{ minWidth: 180, fontFamily: 'monospace' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <strong style={{ color: '#60a5fa', fontSize: 14 }}>{airport.icao}</strong>
                    <span style={{ color: '#9ca3af', fontSize: 12 }}>{formatDate(day.date)}</span>
                  </div>
                  <div style={{ color: '#e5e7eb', fontSize: 12, marginBottom: 6 }}>{airport.name}</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                    <span style={{ color: '#6b7280' }}>Score</span>
                    <strong style={{ color }}>{day.vfr_score.toFixed(0)} — {scoreLabel(day.vfr_score)}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                    <span style={{ color: '#6b7280' }}>Wind</span>
                    <span style={{ color: '#e5e7eb' }}>
                      {day.wind_dir != null ? `${day.wind_dir}°@` : ''}{day.wind_kt.toFixed(0)} kt
                      {day.gust_kt > 0 ? ` G${day.gust_kt.toFixed(0)}` : ''}
                    </span>
                  </div>
                  {day.ceiling_ft != null && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                      <span style={{ color: '#6b7280' }}>Ceiling</span>
                      <span style={{ color: '#e5e7eb' }}>{day.ceiling_ft.toLocaleString()} ft</span>
                    </div>
                  )}
                  {day.visibility_sm != null && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                      <span style={{ color: '#6b7280' }}>Vis</span>
                      <span style={{ color: '#e5e7eb' }}>{day.visibility_sm} sm</span>
                    </div>
                  )}
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                    <span style={{ color: '#6b7280' }}>Precip</span>
                    <span style={{ color: '#e5e7eb' }}>{day.precip_probability.toFixed(0)}%</span>
                  </div>
                  {day.issues.length > 0 && (
                    <div style={{ marginTop: 6, paddingTop: 6, borderTop: '1px solid #374151', color: '#fb923c', fontSize: 11 }}>
                      {day.issues.map((iss, i) => <div key={i}>⚠ {iss}</div>)}
                    </div>
                  )}
                  <div style={{ marginTop: 6, color: '#4b5563', fontSize: 11, textTransform: 'capitalize' }}>
                    {day.confidence} confidence · {day.source.replace('_', ' ')}
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          )
        })}
      </MapContainer>
    </div>
  )
}
