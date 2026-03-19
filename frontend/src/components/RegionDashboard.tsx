import { useState } from 'react'
import type { RegionResponse, AirportForecast, DayForecast, Advisory } from '../types/forecast'
import { scoreBgClass, scoreLabel, formatDate } from '../lib/score'
import ForecastTable from './ForecastTable'

function WeatherTooltip({ day, icao }: { day: DayForecast; icao: string }) {
  return (
    <div className="absolute z-20 bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 bg-gray-800 border border-gray-600 rounded-lg shadow-xl text-xs text-left pointer-events-none">
      <div className="px-3 py-2 border-b border-gray-700 flex items-center justify-between gap-2">
        <span className="font-mono font-bold text-blue-400">{icao}</span>
        <span className="text-gray-400">{formatDate(day.date)}</span>
      </div>
      <div className="px-3 py-2 space-y-1 text-gray-300">
        <div className="flex justify-between">
          <span className="text-gray-500">Score</span>
          <span className={`font-bold ${scoreLabel(day.vfr_score) === 'VFR' ? 'text-green-400' : scoreLabel(day.vfr_score) === 'MVFR' ? 'text-lime-400' : 'text-orange-400'}`}>
            {day.vfr_score.toFixed(0)} — {scoreLabel(day.vfr_score)}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Wind</span>
          <span>{day.wind_kt.toFixed(0)} kt{day.gust_kt > 0 ? ` G${day.gust_kt.toFixed(0)}` : ''}</span>
        </div>
        {day.visibility_sm != null && (
          <div className="flex justify-between">
            <span className="text-gray-500">Vis</span>
            <span>{day.visibility_sm} sm</span>
          </div>
        )}
        {day.ceiling_ft != null && (
          <div className="flex justify-between">
            <span className="text-gray-500">Ceiling</span>
            <span>{day.ceiling_ft.toLocaleString()} ft</span>
          </div>
        )}
        <div className="flex justify-between">
          <span className="text-gray-500">Precip</span>
          <span>{day.precip_probability.toFixed(0)}%</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Clouds</span>
          <span>{day.cloud_cover_pct.toFixed(0)}%</span>
        </div>
        {day.issues.length > 0 && (
          <div className="pt-1 border-t border-gray-700 text-orange-400 space-y-0.5">
            {day.issues.map((iss, i) => <div key={i}>⚠ {iss}</div>)}
          </div>
        )}
        <div className="pt-1 border-t border-gray-700 text-gray-600 capitalize">{day.confidence} confidence · {day.source.replace('_', ' ')}</div>
      </div>
    </div>
  )
}

function AdvisoryBadges({ advisories }: { advisories: Advisory[] }) {
  if (!advisories.length) return null
  const hasSigmet = advisories.some(a => a.type === 'SIGMET')
  const hasConv   = advisories.some(a => a.hazard === 'conv')
  const hasTurb   = advisories.some(a => a.hazard.startsWith('turb'))
  const hasLlws   = advisories.some(a => a.hazard === 'llws')
  return (
    <div className="flex gap-1 flex-wrap mt-0.5">
      {hasSigmet && <span className="text-xs bg-red-600 text-white rounded px-1 py-0.5 font-bold">SIGMET</span>}
      {hasConv   && <span className="text-xs bg-orange-500 text-white rounded px-1 py-0.5">CONV</span>}
      {hasTurb   && <span className="text-xs bg-yellow-500 text-gray-900 rounded px-1 py-0.5">TURB</span>}
      {hasLlws   && <span className="text-xs bg-purple-500 text-white rounded px-1 py-0.5">LLWS</span>}
    </div>
  )
}

const MI_TO_NM = 0.868976
const NM_TO_MI = 1.15078

// Canonical radius options in NM; converted to miles for the API
const RADIUS_OPTIONS_NM = [50, 100, 150, 200, 250]
const RADIUS_OPTIONS_MI = RADIUS_OPTIONS_NM.map(nm => Math.round(nm * NM_TO_MI))

function fmtDist(miles: number, useNm: boolean): string {
  if (useNm) return `${Math.round(miles * MI_TO_NM)} nm`
  return `${miles} mi`
}

interface Props {
  data: RegionResponse
  radius: number
  onRadiusChange: (r: number) => void
  maxAirports: number
  onMaxAirportsChange: (n: number) => void
  useNm: boolean
}

function ScorePill({ score, day, icao }: { score: number; day: DayForecast; icao: string }) {
  const [hovered, setHovered] = useState(false)
  return (
    <div className="relative" onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}>
      <div className={`${scoreBgClass(score)} text-gray-900 text-xs font-bold text-center rounded py-1 px-0.5 min-w-0 cursor-default`}>
        {score.toFixed(0)}
      </div>
      {hovered && <WeatherTooltip day={day} icao={icao} />}
    </div>
  )
}

function AirportRow({
  airport,
  days,
  onClick,
  selected,
  useNm,
}: {
  airport: AirportForecast
  days: DayForecast[]
  onClick: () => void
  selected: boolean
  useNm: boolean
}) {
  return (
    <tr
      onClick={onClick}
      className={`border-b border-gray-800 cursor-pointer transition-colors ${
        selected ? 'bg-blue-900/40 hover:bg-blue-900/50' : 'hover:bg-gray-800/40'
      }`}
    >
      {/* Airport ID + name */}
      <td className="py-2 pr-3 pl-2 whitespace-nowrap">
        <div className="font-mono font-bold text-blue-400 text-sm">{airport.icao}</div>
        <div className="text-gray-500 text-xs truncate max-w-[10rem]">{airport.name}</div>
        {airport.distance_miles != null && airport.distance_miles > 0 && (
          <div className="text-gray-600 text-xs">{fmtDist(airport.distance_miles, useNm)}</div>
        )}
        <AdvisoryBadges advisories={airport.advisories} />
      </td>

      {/* Current score */}
      <td className="py-2 pr-3">
        <div className={`${scoreBgClass(airport.current_score)} text-gray-900 text-xs font-bold text-center rounded px-2 py-1`}>
          {airport.current_score.toFixed(0)}
        </div>
        <div className="text-gray-600 text-xs text-center mt-0.5">now</div>
      </td>

      {/* Day columns */}
      {days.map((day) => (
        <td key={day.date} className="py-2 px-0.5 relative">
          <ScorePill score={day.vfr_score} day={day} icao={airport.icao} />
        </td>
      ))}
    </tr>
  )
}

const MAX_AIRPORTS_OPTIONS = [10, 20, 30, 50]

export default function RegionDashboard({ data, radius, onRadiusChange, maxAirports, onMaxAirportsChange, useNm }: Props) {
  const [selectedIcao, setSelectedIcao] = useState<string | null>(null)

  const selectedAirport = data.airports.find((a) => a.icao === selectedIcao) ?? null

  // Use day columns from the base airport (all airports share the same dates)
  const dayHeaders = data.airports[0]?.daily_forecasts ?? []

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-gray-400 text-sm">Radius:</span>
          {RADIUS_OPTIONS_NM.map((nm, i) => {
            const mi = RADIUS_OPTIONS_MI[i]
            return (
              <button
                key={nm}
                onClick={() => onRadiusChange(mi)}
                className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                  radius === mi
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                }`}
              >
                {nm} nm
              </button>
            )
          })}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-gray-400 text-sm">Max airports:</span>
          {MAX_AIRPORTS_OPTIONS.map((n) => (
            <button
              key={n}
              onClick={() => onMaxAirportsChange(n)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                maxAirports === n
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {n}
            </button>
          ))}
        </div>
        <span className="text-gray-600 text-sm">{data.airport_count} shown</span>
      </div>

      {/* Grid */}
      <div className="bg-gray-900 rounded-xl overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-gray-700">
              <th className="text-left py-2 pl-2 pr-3 text-gray-400 font-medium whitespace-nowrap">Airport</th>
              <th className="text-center py-2 pr-3 text-gray-400 font-medium whitespace-nowrap">Now</th>
              {dayHeaders.map((day, i) => (
                <th key={day.date} className="text-center py-2 px-0.5 text-gray-400 font-medium min-w-[2.5rem]">
                  <div className="text-xs">{formatDate(day.date).split(',')[0]}</div>
                  <div className="text-gray-600 text-xs">{formatDate(day.date).split(' ').slice(1).join(' ')}</div>
                  {i === 0 && <div className="text-blue-400 text-xs">Today</div>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.airports.map((airport) => (
              <AirportRow
                key={airport.icao}
                airport={airport}
                days={airport.daily_forecasts}
                selected={selectedIcao === airport.icao}
                onClick={() =>
                  setSelectedIcao((prev) => (prev === airport.icao ? null : airport.icao))
                }
                useNm={useNm}
              />
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-gray-600">
        Click any row to expand the full 14-day detail. Scores 0–100 (green = VFR, red = IFR).
      </p>

      {/* Expanded detail panel */}
      {selectedAirport && (
        <div className="mt-2">
          <ForecastTable data={selectedAirport} />
        </div>
      )}
    </div>
  )
}
