import type { AirportForecast, DayForecast, Advisory, Runway } from '../types/forecast'
import { formatDate, confidenceBadge, scoreLabel } from '../lib/score'
import ScoreCell from './ScoreCell'

interface Props {
  data: AirportForecast
}

function DayDetail({ day }: { day: DayForecast }) {
  return (
    <div className="text-xs text-gray-400 space-y-0.5">
      <div>Wind: {day.wind_kt.toFixed(0)} kt{day.gust_kt > 0 ? ` (G${day.gust_kt.toFixed(0)})` : ''}</div>
      {day.visibility_sm != null && <div>Vis: {day.visibility_sm} sm</div>}
      {day.ceiling_ft != null && <div>Ceil: {day.ceiling_ft.toLocaleString()} ft</div>}
      <div>Precip: {day.precip_probability.toFixed(0)}%</div>
      {day.issues.length > 0 && (
        <div className="text-orange-400 mt-1">
          {day.issues.map((iss, i) => <div key={i}>⚠ {iss}</div>)}
        </div>
      )}
    </div>
  )
}

const ADVISORY_STYLE: Record<string, string> = {
  SIGMET: 'bg-red-900/40 border-red-700/50 text-red-300',
  conv:   'bg-orange-900/40 border-orange-700/50 text-orange-300',
  turb:   'bg-yellow-900/40 border-yellow-700/50 text-yellow-200',
  'turb-hi': 'bg-yellow-900/40 border-yellow-700/50 text-yellow-200',
  'turb-lo': 'bg-yellow-900/40 border-yellow-700/50 text-yellow-200',
  llws:   'bg-purple-900/40 border-purple-700/50 text-purple-200',
}

function advisoryStyle(a: Advisory): string {
  if (a.type === 'SIGMET') return ADVISORY_STYLE.SIGMET
  return ADVISORY_STYLE[a.hazard] ?? 'bg-gray-800 border-gray-700 text-gray-300'
}

function AdvisoryPanel({ advisories }: { advisories: Advisory[] }) {
  if (!advisories.length) return null
  return (
    <div className="space-y-2">
      <div className="text-sm font-semibold text-gray-300">Active Advisories</div>
      {advisories.map((a, i) => (
        <div key={i} className={`border rounded-lg px-4 py-3 ${advisoryStyle(a)}`}>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-sm">{a.type}</span>
            <span className="font-medium">{a.label}</span>
            {a.severity && <span className="text-xs opacity-75">{a.severity}</span>}
            {a.altitude  && <span className="text-xs opacity-75">{a.altitude}</span>}
            {a.valid_until && <span className="text-xs opacity-60">until {a.valid_until}</span>}
          </div>
          {a.raw && (
            <div className="mt-2 font-mono text-xs opacity-70 break-all">{a.raw}</div>
          )}
        </div>
      ))}
    </div>
  )
}

function RunwayPanel({ runways }: { runways: Runway[] }) {
  if (!runways.length) return null
  return (
    <div className="space-y-1.5">
      <div className="text-sm font-semibold text-gray-300">Runways</div>
      <div className="flex flex-wrap gap-2">
        {runways.map((rw, i) => (
          <div key={i} className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-300 space-y-0.5">
            <div className="font-mono font-bold text-white">{rw.le}/{rw.he}</div>
            {rw.length_ft && <div>{rw.length_ft.toLocaleString()} ft{rw.width_ft ? ` × ${rw.width_ft} ft` : ''}</div>}
            {rw.surface && <div className="text-gray-500">{rw.surface}</div>}
            <div className="text-gray-500">{rw.lighted ? '💡 Lighted' : 'No lights'}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function ForecastTable({ data }: Props) {
  return (
    <div className="bg-gray-900 rounded-xl p-6 space-y-4">
      {/* Header */}
      <div className="flex items-baseline gap-3">
        <h2 className="text-2xl font-bold font-mono text-white">{data.icao}</h2>
        <span className="text-gray-400">{data.name}</span>
        {data.elevation_ft != null && (
          <span className="text-gray-500 text-sm">{data.elevation_ft.toLocaleString()} ft MSL</span>
        )}
      </div>

      {/* Runways */}
      <RunwayPanel runways={data.runways} />

      {/* Active advisories */}
      <AdvisoryPanel advisories={data.advisories} />

      {/* Current METAR */}
      {data.current_metar && (
        <div className="bg-gray-800 rounded-lg px-4 py-2 font-mono text-xs text-green-400 break-all">
          {data.current_metar}
        </div>
      )}

      {/* Current score summary */}
      <div className="flex items-center gap-3">
        <ScoreCell score={data.current_score} showLabel className="px-4 py-2 text-base" />
        <span className="text-gray-400 text-sm">Current conditions</span>
      </div>

      {/* 14-day table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-gray-700">
              <th className="text-left py-2 pr-4 text-gray-400 font-medium">Date</th>
              <th className="text-center py-2 px-2 text-gray-400 font-medium">Score</th>
              <th className="text-left py-2 px-4 text-gray-400 font-medium hidden md:table-cell">Conditions</th>
              <th className="text-center py-2 pl-2 text-gray-400 font-medium">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {data.daily_forecasts.map((day, i) => (
              <tr
                key={day.date}
                className={`border-b border-gray-800 ${i === 0 ? 'bg-gray-800/50' : 'hover:bg-gray-800/30'} transition-colors`}
              >
                <td className="py-2 pr-4 whitespace-nowrap">
                  <div className="font-medium text-white">{formatDate(day.date)}</div>
                  {i === 0 && <div className="text-xs text-blue-400">Today</div>}
                </td>
                <td className="py-2 px-2">
                  <ScoreCell score={day.vfr_score} className="px-3 py-1 mx-auto w-16" />
                </td>
                <td className="py-2 px-4 hidden md:table-cell">
                  <DayDetail day={day} />
                </td>
                <td className="py-2 pl-2 text-center">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${confidenceBadge(day.confidence)}`}>
                    {day.confidence.toUpperCase()}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Best days callout */}
      {(() => {
        const best = data.daily_forecasts.filter(d => d.vfr_score >= 70).slice(0, 3)
        if (!best.length) return null
        return (
          <div className="bg-green-900/30 border border-green-700/50 rounded-lg px-4 py-3">
            <div className="text-green-400 font-medium mb-1">Best days for flying:</div>
            <div className="space-y-0.5">
              {best.map(d => (
                <div key={d.date} className="text-sm flex gap-2">
                  <span className="text-white">{formatDate(d.date)}</span>
                  <span className="text-green-400">{scoreLabel(d.vfr_score)} ({d.vfr_score.toFixed(0)})</span>
                </div>
              ))}
            </div>
          </div>
        )
      })()}

      {/* Disclaimer */}
      <p className="text-xs text-gray-600">
        For planning reference only. Always obtain a full weather briefing before flight.
        Verify NOTAMs, winds aloft, and TFRs before departure.
      </p>
    </div>
  )
}
