import './ScoreDeltaToast.css'

interface ScoreDeltaToastProps {
  id: string
  delta: number
  playerName: string
  onDone: (id: string) => void
}

export default function ScoreDeltaToast({ id, delta, playerName, onDone }: ScoreDeltaToastProps) {
  const color = delta > 0 ? '#22c55e' : delta < 0 ? '#ef4444' : '#6b7280'
  const label = delta > 0 ? `+${delta}` : `${delta}`

  return (
    <div
      className="score-delta-toast"
      style={{ color }}
      aria-label={`${playerName}: ${label} pontos`}
      onAnimationEnd={() => onDone(id)}
    >
      {label}
    </div>
  )
}
