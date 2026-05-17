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
  ROUND_START: 'var(--phase-start)',
  HINT_PHASE: 'var(--phase-hint)',
  GUESS_PHASE: 'var(--phase-guess)',
  EXCHANGE_PHASE: 'var(--phase-exchange)',
  SPY_PHASE: 'var(--phase-spy)',
  SCORING_PHASE: 'var(--phase-scoring)',
  TURN_END: 'var(--phase-start)',
  GAME_ENDED: 'var(--phase-ended)',
}

const DEFAULT_COLOR = 'var(--phase-ended)'

export default function PhaseBadge({ phase }: PhaseBadgeProps) {
  const label = PHASE_LABELS[phase] ?? phase
  const backgroundColor = PHASE_COLORS[phase] ?? DEFAULT_COLOR

  return (
    <span
      style={{
        backgroundColor,
        color: 'var(--color-text-inverse)',
        padding: '4px 10px',
        borderRadius: '9999px',
        fontSize: '13px',
        fontWeight: 700,
        letterSpacing: '0',
      }}
      aria-label={`Fase atual: ${label}`}
    >
      {label}
    </span>
  )
}
