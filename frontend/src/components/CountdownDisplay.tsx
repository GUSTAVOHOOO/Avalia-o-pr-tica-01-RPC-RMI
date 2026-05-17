interface CountdownDisplayProps {
  seconds: number
}

function timerColor(seconds: number): string {
  if (seconds <= 5) return '#ef4444'   // red (D-12)
  if (seconds <= 10) return '#eab308'  // amber (D-12)
  return '#22c55e'                     // green (D-12)
}

export default function CountdownDisplay({ seconds }: CountdownDisplayProps) {
  return (
    <span
      style={{
        fontSize: '28px',
        fontWeight: 600,
        color: timerColor(seconds),
        transition: 'color 0.3s ease',
      }}
      aria-live="polite"
    >
      {seconds}s
    </span>
  )
}
