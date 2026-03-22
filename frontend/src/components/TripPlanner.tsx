import { useState, useRef, useEffect } from 'react'
import type { TripDayScore, AirportForecast } from '../types/forecast'
import { scoreBgClass, scoreLabel, formatDate, confidenceBadge } from '../lib/score'
import { useTrip } from '../hooks/useTrip'
import ForecastTable from './ForecastTable'

// ── Airport search input ──────────────────────────────────────────────────────

interface AirportOption { icao: string; name: string }

function AirportInput({
  label,
  value,
  onSelect,
}: {
  label: string
  value: string | null
  onSelect: (icao: string) => void
}) {
  const [query, setQuery] = useState(value ?? '')
  const [results, setResults] = useState<AirportOption[]>([])
  const [open, setOpen] = useState(false)
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (value && query !== value) setQuery(value)
  }, [value]) // eslint-disable-line react-hooks/exhaustive-deps

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const q = e.target.value
    setQuery(q)
    if (debounce.current) clearTimeout(debounce.current)
    if (q.length < 1) { setResults([]); setOpen(false); return }
    debounce.current = setTimeout(async () => {
      try {
        const res = await fetch(`/api/v1/airports/search?q=${encodeURIComponent(q)}`)
        const data: AirportOption[] = await res.json()
        setResults(data)
        setOpen(true)
      } catch { setResults([]) }
    }, 200)
  }

  function handleSelect(opt: AirportOption) {
    setQuery(opt.icao)
    setOpen(false)
    onSelect(opt.icao)
  }

  return (
    <div className="relative flex-1 min-w-[140px]">
      <label className="block text-xs text-gray-500 mb-1">{label}</label>
      <input
        value={query}
        onChange={handleChange}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onFocus={() => results.length > 0 && setOpen(true)}
        placeholder="e.g. KBDN"
        className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
      />
      {open && results.length > 0 && (
        <ul className="absolute z-30 top-full left-0 right-0 mt-1 bg-gray-900 border border-gray-700 rounded-lg shadow-xl overflow-y-auto max-h-64">
          {results.map(opt => (
            <li
              key={opt.icao}
              onMouseDown={() => handleSelect(opt)}
              className="px-3 py-2 hover:bg-gray-700 cursor-pointer flex items-center gap-3"
            >
              <span className="font-mono text-blue-400 text-sm w-12 shrink-0">{opt.icao}</span>
              <span className="text-gray-300 text-sm truncate">{opt.name}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ── Day score row ─────────────────────────────────────────────────────────────

function DayScoreRow({
  ds,
  airports,
  isToday,
}: {
  ds: TripDayScore
  airports: AirportForecast[]
  isToday: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  const limiting = airports.find(a => a.icao === ds.limiting_icao)

  return (
    <>
      <tr
        className={`border-b border-gray-800 cursor-pointer transition-colors ${
          isToday ? 'bg-gray-800/50' : 'hover:bg-gray-800/30'
        }`}
        onClick={() => setExpanded(v => !v)}
      >
        <td className="py-2 pr-3 whitespace-nowrap">
          <div className="font-medium text-white text-sm">{formatDate(ds.date)}</div>
          {isToday && <div className="text-xs text-blue-400">Today</div>}
        </td>
        <td className="py-2 px-2">
          <div className={`${scoreBgClass(ds.trip_score)} text-gray-900 text-xs font-bold text-center rounded px-3 py-1.5 w-14`}>
            {ds.trip_score.toFixed(0)}
          </div>
          <div className="text-xs text-center text-gray-500 mt-0.5">{scoreLabel(ds.trip_score)}</div>
        </td>
        <td className="py-2 px-3 text-sm text-gray-400">
          <span className="font-mono text-orange-400">{ds.limiting_icao}</span>
          <span className="text-gray-600 ml-1.5 text-xs">{ds.limiting_name}</span>
        </td>
        <td className="py-2 pl-2 text-center">
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${confidenceBadge(ds.confidence)}`}>
            {ds.confidence.toUpperCase()}
          </span>
        </td>
        <td className="py-2 pl-2 text-center text-gray-600 text-xs">
          {expanded ? '▲' : '▼'}
        </td>
      </tr>
      {expanded && limiting && (
        <tr>
          <td colSpan={5} className="pb-4 pt-1 px-2">
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
              <div className="text-xs text-gray-500 mb-3">
                Limiting airport detail — worst score on this day
              </div>
              <ForecastTable data={limiting} />
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

// ── Corridor airport list ─────────────────────────────────────────────────────

function CorridorAirports({ airports }: { airports: AirportForecast[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {airports.map((a, i) => (
        <div
          key={a.icao}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs border ${
            i === 0 || i === airports.length - 1
              ? 'bg-blue-900/30 border-blue-700/50 text-blue-300'
              : 'bg-gray-800 border-gray-700 text-gray-300'
          }`}
        >
          {i > 0 && i < airports.length - 1 && (
            <span className="text-gray-600">·</span>
          )}
          <span className="font-mono font-semibold">{a.icao}</span>
          <span className="text-gray-500 hidden sm:inline">{a.name.split('/')[0].trim()}</span>
        </div>
      ))}
    </div>
  )
}

// ── Best days callout ─────────────────────────────────────────────────────────

function BestDays({ scores }: { scores: TripDayScore[] }) {
  const good = scores.filter(d => d.trip_score >= 70).slice(0, 5)
  if (!good.length) return null
  return (
    <div className="bg-green-900/20 border border-green-700/40 rounded-xl px-4 py-3">
      <div className="text-xs text-green-400 font-semibold mb-2">Best days to fly this trip</div>
      <div className="flex flex-wrap gap-2">
        {good.map(d => (
          <div key={d.date} className={`${scoreBgClass(d.trip_score)} text-gray-900 rounded px-2 py-0.5 text-xs font-bold`}>
            {formatDate(d.date)} · {d.trip_score.toFixed(0)}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  useNm: boolean
  minRwyFt: number
  onMinRwyFtChange: (v: number) => void
}

export default function TripPlanner({ useNm, minRwyFt, onMinRwyFtChange }: Props) {
  const [origin, setOrigin] = useState<string | null>(null)
  const [dest, setDest] = useState<string | null>(null)
  const [corridorWidth, setCorridorWidth] = useState(50)
  const [maxAirports, setMaxAirports] = useState(15)

  const { data, isLoading, isError, error } = useTrip(
    origin, dest, corridorWidth, maxAirports, minRwyFt,
  )

  const today = new Date().toISOString().slice(0, 10)

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-4">
        <div className="flex flex-wrap gap-4 items-end">
          <AirportInput label="Origin" value={origin} onSelect={setOrigin} />
          <div className="text-gray-600 text-xl pb-2 self-end">→</div>
          <AirportInput label="Destination" value={dest} onSelect={setDest} />
        </div>

        <div className="flex flex-wrap gap-6 text-sm">
          <label className="flex items-center gap-2 text-gray-400">
            <span className="text-xs">Corridor width ({useNm ? 'NM' : 'mi'})</span>
            <input
              type="number"
              min={10}
              max={150}
              value={useNm ? Math.round(corridorWidth / 1.151) : corridorWidth}
              onChange={e => {
                const v = Number(e.target.value)
                setCorridorWidth(useNm ? Math.round(v * 1.151) : v)
              }}
              className="w-16 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-xs focus:outline-none focus:border-blue-500"
            />
          </label>

          <label className="flex items-center gap-2 text-gray-400">
            <span className="text-xs">Max airports</span>
            <input
              type="number"
              min={2}
              max={50}
              value={maxAirports}
              onChange={e => setMaxAirports(Number(e.target.value))}
              className="w-16 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-xs focus:outline-none focus:border-blue-500"
            />
          </label>

          <label className="flex items-center gap-2 text-gray-400">
            <span className="text-xs">Min runway (ft)</span>
            <input
              type="number"
              min={0}
              step={500}
              value={minRwyFt}
              onChange={e => onMinRwyFtChange(Number(e.target.value))}
              className="w-20 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-xs focus:outline-none focus:border-blue-500"
            />
          </label>
        </div>
      </div>

      {/* Empty state */}
      {!origin && !dest && (
        <div className="text-center py-20 text-gray-500">
          <div className="text-5xl mb-4">✈</div>
          <p className="text-lg">Enter origin and destination airports</p>
          <p className="text-sm mt-2 text-gray-600">
            Shows 14-day corridor forecast — score is the worst airport along the route
          </p>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="text-center py-20 text-gray-400">
          <div className="animate-spin text-4xl mb-4">⟳</div>
          <p>Fetching corridor forecasts for {origin} → {dest}…</p>
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="bg-red-900/30 border border-red-700/50 rounded-xl p-6 text-center">
          <div className="text-red-400 font-medium mb-1">Could not load trip forecast</div>
          <div className="text-red-300 text-sm">{error?.message}</div>
        </div>
      )}

      {/* Results */}
      {data && !isLoading && (
        <div className="space-y-4">
          {/* Trip header */}
          <div className="flex flex-wrap items-center gap-3 text-sm text-gray-400">
            <span className="font-mono text-white font-bold text-base">{data.origin}</span>
            <span className="text-gray-600">{data.origin_name}</span>
            <span className="text-gray-600">→</span>
            <span className="font-mono text-white font-bold text-base">{data.dest}</span>
            <span className="text-gray-600">{data.dest_name}</span>
            <span className="text-gray-700">·</span>
            <span>{useNm ? `${Math.round(data.corridor_miles / 1.151)} NM` : `${data.corridor_miles.toFixed(0)} mi`}</span>
            <span className="text-gray-700">·</span>
            <span>{data.airport_count} airports sampled</span>
          </div>

          {/* Corridor airports */}
          <CorridorAirports airports={data.airports} />

          {/* Best days */}
          <BestDays scores={data.daily_scores} />

          {/* 14-day table */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-800 text-sm text-gray-400">
              14-day corridor forecast · score = worst airport on that day · click a row for detail
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-500 text-xs uppercase tracking-tight">
                    <th className="text-left py-2 pr-3 pl-4">Date</th>
                    <th className="text-center py-2 px-2">Score</th>
                    <th className="text-left py-2 px-3">Limiting airport</th>
                    <th className="text-center py-2 pl-2">Confidence</th>
                    <th className="py-2 pl-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {data.daily_scores.map(ds => (
                    <DayScoreRow
                      key={ds.date}
                      ds={ds}
                      airports={data.airports}
                      isToday={ds.date === today}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
