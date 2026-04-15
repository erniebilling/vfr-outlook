import { useState, useRef } from 'react'
import type { RegionResponse, AirportForecast, DayForecast, Advisory } from '../types/forecast'
import { scoreBgClass, scoreLabel, formatDate } from '../lib/score'
import ForecastTable from './ForecastTable'
import RegionMap from './RegionMap'

function WeatherTooltip({ day, icao, x, y }: { day: DayForecast; icao: string; x: number; y: number }) {
  return (
    <div className="fixed w-44 max-w-[90vw] bg-gray-800 border border-gray-600 rounded-lg shadow-xl text-xs text-left pointer-events-none"
      style={{ left: x, top: y, transform: 'translate(-50%, -100%) translateY(-8px)', zIndex: 1000 }}
    >
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

const RADIUS_OPTIONS = [50, 100, 150, 200, 250]

function fmtDist(miles: number, useNm: boolean): string {
  if (useNm) return `${Math.round(miles * MI_TO_NM)} nm`
  return `${miles} mi`
}

const MIN_RWY_OPTIONS = [0, 2000, 3000, 4000, 5000]
const MAX_AIRPORTS_OPTIONS = [10, 20, 30, 50]

interface Props {
  data: RegionResponse
  radius: number
  onRadiusChange: (r: number) => void
  maxAirports: number
  onMaxAirportsChange: (n: number) => void
  useNm: boolean
  minRwyFt: number
  onMinRwyFtChange: (ft: number) => void
}

function ScorePill({
  score, day, icao, active,
}: {
  score: number; day: DayForecast; icao: string; active: boolean
}) {
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null)
  const pillRef = useRef<HTMLDivElement>(null)

  function handleMouseEnter() {
    if (pillRef.current) {
      const r = pillRef.current.getBoundingClientRect()
      setPos({ x: r.left + r.width / 2, y: r.top })
    }
  }

  return (
    <div
      ref={pillRef}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={() => setPos(null)}
    >
      <div className={`${scoreBgClass(score)} text-gray-900 text-xs font-bold text-center rounded py-1 px-0.5 min-w-0 cursor-default transition-all ${active ? 'ring-2 ring-white ring-offset-1 ring-offset-gray-900' : ''}`}>
        {score.toFixed(0)}
      </div>
      {pos && <WeatherTooltip day={day} icao={icao} x={pos.x} y={pos.y} />}
    </div>
  )
}

function AirportRow({
  airport, days, onClick, selected, useNm, activeDayIndex,
}: {
  airport: AirportForecast
  days: DayForecast[]
  onClick: () => void
  selected: boolean
  useNm: boolean
  activeDayIndex: number
}) {
  return (
    <tr
      onClick={onClick}
      className={`border-b border-gray-800 cursor-pointer transition-colors ${
        selected ? 'bg-blue-900/40 hover:bg-blue-900/50' : 'hover:bg-gray-800/40'
      }`}
    >
      <td className="py-2 pr-3 pl-2 whitespace-nowrap">
        <div className="font-mono font-bold text-blue-400 text-sm">{airport.icao}</div>
        <div className="text-gray-500 text-xs truncate max-w-[10rem]">{airport.name}</div>
        {airport.distance_miles != null && airport.distance_miles > 0 && (
          <div className="text-gray-600 text-xs">{fmtDist(airport.distance_miles, useNm)}</div>
        )}
        <AdvisoryBadges advisories={airport.advisories} />
      </td>

      <td className="py-2 pr-3">
        {airport.current_metar ? (
          <>
            <div className={`${scoreBgClass(airport.current_score)} text-gray-900 text-xs font-bold text-center rounded px-2 py-1`}>
              {airport.current_score.toFixed(0)}
            </div>
            <div className="text-gray-600 text-xs text-center mt-0.5">now</div>
          </>
        ) : (
          <div className="text-gray-700 text-xs text-center">—</div>
        )}
      </td>

      {days.map((day, i) => (
        <td key={day.date} className="py-2 px-0.5 relative">
          <ScorePill score={day.vfr_score} day={day} icao={airport.icao} active={i === activeDayIndex} />
        </td>
      ))}
    </tr>
  )
}

// Day slider with play/pause animation
function DaySlider({
  days,
  activeDayIndex,
  onDayChange,
}: {
  days: DayForecast[]
  activeDayIndex: number
  onDayChange: (i: number) => void
}) {
  const activeDay = days[activeDayIndex]
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-white">
          {activeDay ? formatDate(activeDay.date) : ''}
        </span>
        <span className="text-xs text-gray-500">
          {activeDayIndex === 0 ? 'Today' : `Day +${activeDayIndex}`} · map colors update with slider
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={days.length - 1}
        value={activeDayIndex}
        onChange={e => onDayChange(Number(e.target.value))}
        className="w-full accent-blue-500 cursor-pointer"
      />
      <div className="flex justify-between text-xs text-gray-600 pointer-events-none select-none">
        {days.map((d, i) => (
          <span
            key={d.date}
            className={i === activeDayIndex ? 'text-blue-400 font-bold' : ''}
          >
            {i % 2 === 0 ? formatDate(d.date).split(' ')[1] : ''}
          </span>
        ))}
      </div>
    </div>
  )
}

export default function RegionDashboard({
  data, radius, onRadiusChange, maxAirports, onMaxAirportsChange, useNm, minRwyFt, onMinRwyFtChange,
}: Props) {
  const [selectedIcao, setSelectedIcao] = useState<string | null>(null)
  const [activeDayIndex, setActiveDayIndex] = useState(0)
  const [showMap, setShowMap] = useState(true)

  const selectedAirport = data.airports.find(a => a.icao === selectedIcao) ?? null
  const dayHeaders = data.airports[0]?.daily_forecasts ?? []

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-gray-400 text-sm">Radius:</span>
          {RADIUS_OPTIONS.map(r => {
            const rMi = useNm ? Math.round(r * NM_TO_MI) : r
            return (
              <button
                key={r}
                onClick={() => onRadiusChange(rMi)}
                className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                  radius === rMi ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                }`}
              >
                {r}
              </button>
            )
          })}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-gray-400 text-sm">Max airports:</span>
          {MAX_AIRPORTS_OPTIONS.map(n => (
            <button
              key={n}
              onClick={() => onMaxAirportsChange(n)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                maxAirports === n ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {n}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-gray-400 text-sm">Min runway:</span>
          {MIN_RWY_OPTIONS.map(ft => (
            <button
              key={ft}
              onClick={() => onMinRwyFtChange(ft)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                minRwyFt === ft ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {ft === 0 ? 'Any' : `${(ft / 1000).toFixed(0)}k`}
            </button>
          ))}
        </div>
        <span className="text-gray-600 text-sm">{data.airport_count} shown</span>
        <button
          onClick={() => setShowMap(v => !v)}
          className="ml-auto text-xs px-3 py-1.5 rounded border border-gray-700 bg-gray-800 hover:bg-gray-700 transition-colors text-gray-300"
        >
          {showMap ? 'Hide map' : 'Show map'}
        </button>
      </div>

      {/* Day slider — drives both map colors and grid highlight */}
      {dayHeaders.length > 0 && (
        <DaySlider
          days={dayHeaders}
          activeDayIndex={activeDayIndex}
          onDayChange={setActiveDayIndex}
        />
      )}

      {/* Map */}
      {showMap && (
        <RegionMap
          airports={data.airports}
          centerLat={data.base_lat}
          centerLon={data.base_lon}
          radiusMiles={radius}
          dayIndex={activeDayIndex}
          selectedIcao={selectedIcao}
          onSelect={icao => setSelectedIcao(prev => prev === icao ? null : icao)}
        />
      )}

      {/* Grid */}
      <div className="bg-gray-900 rounded-xl overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-gray-700">
              <th className="text-left py-2 pl-2 pr-3 text-gray-400 font-medium whitespace-nowrap">Airport</th>
              <th className="text-center py-2 pr-3 text-gray-400 font-medium whitespace-nowrap">Now</th>
              {dayHeaders.map((day, i) => (
                <th
                  key={day.date}
                  className={`text-center py-2 px-0.5 font-medium min-w-[2.5rem] cursor-pointer transition-colors ${
                    i === activeDayIndex ? 'text-blue-400 bg-blue-900/20' : 'text-gray-400 hover:text-gray-300'
                  }`}
                  onClick={() => setActiveDayIndex(i)}
                >
                  <div className="text-xs">{formatDate(day.date).split(',')[0]}</div>
                  <div className="text-xs opacity-70">{formatDate(day.date).split(' ').slice(1).join(' ')}</div>
                  {i === 0 && <div className="text-blue-400 text-xs">Today</div>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.airports.map(airport => (
              <AirportRow
                key={airport.icao}
                airport={airport}
                days={airport.daily_forecasts}
                selected={selectedIcao === airport.icao}
                onClick={() => setSelectedIcao(prev => prev === airport.icao ? null : airport.icao)}
                useNm={useNm}
                activeDayIndex={activeDayIndex}
              />
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-gray-600">
        Drag the slider or click a column header to change the forecast day shown on the map. Click any row to expand the full detail.
      </p>

      {selectedAirport && (
        <div className="mt-2">
          <ForecastTable data={selectedAirport} />
        </div>
      )}
    </div>
  )
}
