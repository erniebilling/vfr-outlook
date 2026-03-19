import { scoreBgClass, scoreLabel } from '../lib/score'

interface Props {
  score: number
  showLabel?: boolean
  className?: string
}

export default function ScoreCell({ score, showLabel = false, className = '' }: Props) {
  return (
    <div
      className={`${scoreBgClass(score)} rounded text-center font-bold text-gray-900 text-sm ${className}`}
      title={`${scoreLabel(score)} — ${score.toFixed(0)}/100`}
    >
      {score.toFixed(0)}
      {showLabel && <div className="text-xs font-normal opacity-80">{scoreLabel(score)}</div>}
    </div>
  )
}
