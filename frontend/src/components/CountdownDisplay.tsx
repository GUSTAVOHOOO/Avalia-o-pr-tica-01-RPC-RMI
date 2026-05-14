interface CountdownDisplayProps {
  seconds: number
}

export default function CountdownDisplay({ seconds }: CountdownDisplayProps) {
  return (
    <span
      style={{
        fontSize: '28px',
        fontWeight: 600,
        color: '#f1f5f9',
      }}
      aria-live="polite"
    >
      {seconds}s
    </span>
  )
}
