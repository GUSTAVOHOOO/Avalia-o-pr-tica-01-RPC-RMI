interface CountdownDisplayProps {
  seconds: number
}

function timerColor(seconds: number): string {
  if (seconds <= 5) return 'var(--color-danger)'
  if (seconds <= 10) return 'var(--color-warning)'
  return 'var(--color-success)'
}

export default function CountdownDisplay({ seconds }: CountdownDisplayProps) {
  return (
    <span
      style={{
        fontSize: '28px',
        fontWeight: 700,
        color: timerColor(seconds),
        transition: 'color 0.3s ease',
        fontVariantNumeric: 'tabular-nums',
      }}
      aria-live="polite"
    >
      {seconds}s
    </span>
  )
}
