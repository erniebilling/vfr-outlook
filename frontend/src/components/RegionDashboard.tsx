import { useState } from 'react'
import type { RegionResponse, AirportForecast, DayForecast } from '../types/forecast'
import { scoreBgClass, scoreLabel, formatDate } from '../lib/score'
import ForecastTable from './ForecastTable'

interface Props {
  data: RegionResponse
  radius: number
  onRadiusChange: (r: number) => void
}

function ScorePill({ score }: { score: number }) {
  return (
    <div
      className={`${scoreBgClass(score)} text-gray-900 text-xs font-bold text-center rounded py-1 px-0.5 min-w-0`}
      title={`${scoreLabel(score)} — ${score.toFixed(0)}/100`}
    >
      {score.toFixed(0)}
    </div>
  )
}

function AirportRow({
  airport,
  days,
  onClick,
  selected,
}: {
  airport: AirportForecast
  days: DayForecast[]
  onClick: () => void
  selected: boolean
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
          <div className="text-gray-600 text-xs">{airport.distance_miles} mi</div>
        )}
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
        <td key={day.date} className="py-2 px-0.5">
          <ScorePill score={day.vfr_score} />
        </td>
      ))}
    </tr>
  )
}

const RADIUS_OPTIONS = [50, 100, 150, 200, 300]

export default function RegionDashboard({ data, radius, onRadiusChange }: Props) {
  const [selectedIcao, setSelectedIcao] = useState<string | null>(null)

  const selectedAirport = data.airports.find((a) => a.icao === selectedIcao) ?? null

  // Use day columns from the base airport (all airports share the same dates)
  const dayHeaders = data.airports[0]?.daily_forecasts ?? []

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-gray-400 text-sm">Radius:</span>
        {RADIUS_OPTIONS.map((r) => (
          <button
            key={r}
            onClick={() => onRadiusChange(r)}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              radius === r
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
            }`}
          >
            {r} mi
          </button>
        ))}
        <span className="text-gray-600 text-sm ml-2">{data.airport_count} airports</span>
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
