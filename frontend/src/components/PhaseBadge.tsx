interface PhaseBadgeProps {
  phase: string
}

const PHASE_LABELS: Record<string, string> = {
  ROUND_START: 'Início',
  HINT_PHASE: 'DICA',
  GUESS_PHASE: 'PALPITE',
  EXCHANGE_PHASE: 'TROCA',
  SPY_PHASE: 'ESPIONAGEM',
  SCORING_PHASE: 'PONTUAÇÃO',
  TURN_END: 'Calculando...',
  GAME_ENDED: 'Fim de Jogo',
}

const PHASE_COLORS: Record<string, string> = {
  ROUND_START: '#6366f1',
  HINT_PHASE: '#3b82f6',
  GUESS_PHASE: '#22c55e',
  EXCHANGE_PHASE: '#a855f7',
  SPY_PHASE: '#f59e0b',
  SCORING_PHASE: '#eab308',
  TURN_END: '#6366f1',
  GAME_ENDED: '#6b7280',
}

const DEFAULT_COLOR = '#6b7280'

export default function PhaseBadge({ phase }: PhaseBadgeProps) {
  const label = PHASE_LABELS[phase] ?? phase
  const backgroundColor = PHASE_COLORS[phase] ?? DEFAULT_COLOR

  return (
    <span
      style={{
        backgroundColor,
        color: '#f1f5f9',
        padding: '2px 4px',
        borderRadius: '9999px',
        fontSize: '14px',
        fontWeight: 400,
      }}
      aria-label={`Fase atual: ${label}`}
    >
      {label}
    </span>
  )
}
