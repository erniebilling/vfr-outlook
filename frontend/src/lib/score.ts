/**
 * UI helpers for VFR score display.
 */

export function scoreColor(score: number): string {
  if (score >= 85) return '#22c55e'  // green
  if (score >= 65) return '#84cc16'  // lime
  if (score >= 45) return '#eab308'  // yellow
  if (score >= 25) return '#f97316'  // orange
  return '#ef4444'                    // red
}

export function scoreLabel(score: number): string {
  if (score >= 85) return 'VFR'
  if (score >= 65) return 'MVFR'
  if (score >= 45) return 'Marginal'
  if (score >= 25) return 'Poor'
  return 'IFR'
}

export function scoreBgClass(score: number): string {
  if (score >= 85) return 'bg-green-500'
  if (score >= 65) return 'bg-lime-500'
  if (score >= 45) return 'bg-yellow-500'
  if (score >= 25) return 'bg-orange-500'
  return 'bg-red-500'
}

export function confidenceBadge(confidence: string): string {
  switch (confidence) {
    case 'high':   return 'bg-blue-700 text-blue-100'
    case 'medium': return 'bg-gray-600 text-gray-200'
    default:       return 'bg-gray-800 text-gray-400'
  }
}

export function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T12:00:00')
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
}
