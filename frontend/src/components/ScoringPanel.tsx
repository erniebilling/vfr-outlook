import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'

interface ScoringParams {
  criteria: {
    max_wind_kt: number
    min_vis_sm: number
    min_ceiling_ft: number
    max_precip_pct: number
  }
  weights: {
    wind: number
    visibility: number
    ceiling: number
    precip: number
  }
  score_thresholds: {
    vfr: number
    mvfr: number
    marginal: number
    poor: number
  }
  scoring_ranges: {
    wind_kt:    { perfect: number; zero: number }
    vis_sm:     { perfect: number; zero: number }
    ceiling_ft: { perfect: number; zero: number }
    precip_pct: { perfect: number; zero: number }
  }
}

function useScoringParams() {
  return useQuery<ScoringParams, Error>({
    queryKey: ['scoring-params'],
    queryFn: async () => {
      const res = await fetch('/api/v1/scoring-params')
      if (!res.ok) throw new Error('Failed to load scoring parameters')
      return res.json()
    },
    staleTime: Infinity,
  })
}

function Row({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <tr className="border-b border-gray-800 last:border-0">
      <td className="py-1.5 pr-4 text-gray-400 text-sm whitespace-nowrap">{label}</td>
      <td className="py-1.5 pr-4 font-mono text-sm text-white">{value}</td>
      {note && <td className="py-1.5 text-gray-500 text-xs">{note}</td>}
    </tr>
  )
}

export default function ScoringPanel() {
  const [open, setOpen] = useState(false)
  const { data, isLoading, isError } = useScoringParams()

  return (
    <div className="border border-gray-800 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-gray-900 hover:bg-gray-800 transition-colors text-sm text-gray-300"
      >
        <span className="font-medium">Scoring Parameters</span>
        <span className="text-gray-500 text-xs">{open ? '▲ hide' : '▼ show'}</span>
      </button>

      {open && (
        <div className="bg-gray-900/50 px-4 py-4 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {isLoading && <p className="text-gray-500 text-sm col-span-4">Loading…</p>}
          {isError  && <p className="text-red-400 text-sm col-span-4">Could not load scoring parameters.</p>}

          {data && (
            <>
              {/* Personal minimums */}
              <div>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Personal Minimums</h3>
                <table className="w-full">
                  <tbody>
                    <Row label="Max wind"    value={`${data.criteria.max_wind_kt} kt`} />
                    <Row label="Min vis"     value={`${data.criteria.min_vis_sm} sm`} />
                    <Row label="Min ceiling" value={`${data.criteria.min_ceiling_ft.toLocaleString()} ft`} />
                    <Row label="Max precip"  value={`${data.criteria.max_precip_pct}%`} />
                  </tbody>
                </table>
              </div>

              {/* Sub-score weights */}
              <div>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Sub-score Weights</h3>
                <table className="w-full">
                  <tbody>
                    <Row label="Wind"       value={`${(data.weights.wind * 100).toFixed(0)}%`} />
                    <Row label="Visibility" value={`${(data.weights.visibility * 100).toFixed(0)}%`} />
                    <Row label="Ceiling"    value={`${(data.weights.ceiling * 100).toFixed(0)}%`} />
                    <Row label="Precip"     value={`${(data.weights.precip * 100).toFixed(0)}%`} />
                  </tbody>
                </table>
              </div>

              {/* Scoring ranges */}
              <div>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Scoring Ranges (100 → 0)</h3>
                <table className="w-full">
                  <tbody>
                    <Row label="Wind"    value={`≤${data.scoring_ranges.wind_kt.perfect} → ≥${data.scoring_ranges.wind_kt.zero} kt`} />
                    <Row label="Vis"     value={`≥${data.scoring_ranges.vis_sm.perfect} → ≤${data.scoring_ranges.vis_sm.zero} sm`} />
                    <Row label="Ceiling" value={`≥${data.scoring_ranges.ceiling_ft.perfect.toLocaleString()} → ≤${data.scoring_ranges.ceiling_ft.zero} ft`} />
                    <Row label="Precip"  value={`${data.scoring_ranges.precip_pct.perfect}% → ≥${data.scoring_ranges.precip_pct.zero}%`} />
                  </tbody>
                </table>
              </div>

              {/* Score thresholds */}
              <div>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Score Thresholds</h3>
                <table className="w-full">
                  <tbody>
                    <Row label="VFR"      value={`≥ ${data.score_thresholds.vfr}`} />
                    <Row label="MVFR"     value={`≥ ${data.score_thresholds.mvfr}`} />
                    <Row label="Marginal" value={`≥ ${data.score_thresholds.marginal}`} />
                    <Row label="Poor"     value={`≥ ${data.score_thresholds.poor}`} />
                    <Row label="IFR"      value={`< ${data.score_thresholds.poor}`} />
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
