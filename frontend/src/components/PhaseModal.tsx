import PhaseBadge from './PhaseBadge'
import './PhaseModal.css'

/* ─── Interfaces ─────────────────────────────────────────────────────────── */

interface Player {
  player_id: string
  player_name: string
  is_host: boolean
}

interface ExchangeRequest {
  exchange_id: string
  requester_id: string
}

interface PhaseModalProps {
  phase: string
  players: Player[]
  myPlayerId: string
  // HINT
  hintInput: string
  onHintChange: (v: string) => void
  onHintSubmit: () => void
  hintSubmitted: boolean
  hintsCount: number
  totalPlayers: number
  // GUESS
  hints: Record<string, string>
  guessTarget: string
  onGuessTargetChange: (v: string) => void
  guessInput: string
  onGuessInputChange: (v: string) => void
  onGuessSubmit: () => void
  onGuessSkip: () => void
  guessSubmitted: boolean
  guessIsCorrect: boolean | null
  // EXCHANGE
  exchangeRequest: ExchangeRequest | null   // incoming request (recipient view)
  myExchangeId: string | null               // if requester, current exchange_id
  exchangeStatus: string | null             // 'pending'|'accepted'|'rejected'|null
  exchangeHintInput: string
  onExchangeHintChange: (v: string) => void
  onExchangeAccept: () => void
  onExchangeDecline: () => void
  onExchangeHintSubmit: () => void
  exchangeHintSubmitted: boolean
  // SPY
  spyTargets: string[]                      // list of exchange_ids (opaque strings)
  selectedSpyTarget: string
  onSpyTargetSelect: (id: string) => void
  onSpyAttempt: () => void
  spyAttempted: boolean
}

/* ─── Constants ──────────────────────────────────────────────────────────── */

const ACTION_PHASES = ['HINT_PHASE', 'GUESS_PHASE', 'EXCHANGE_PHASE', 'SPY_PHASE']

const PHASE_TITLES: Record<string, string> = {
  HINT_PHASE: 'Fase de Dicas',
  GUESS_PHASE: 'Fase de Palpites',
  EXCHANGE_PHASE: 'Fase de Troca',
  SPY_PHASE: 'Fase de Espionagem',
}

/* ─── Helper ─────────────────────────────────────────────────────────────── */

function playerName(players: Player[], playerId: string): string {
  return players.find((p) => p.player_id === playerId)?.player_name ?? playerId
}

/* ─── Phase variant sub-components ──────────────────────────────────────── */

interface HintVariantProps {
  hintInput: string
  onHintChange: (v: string) => void
  onHintSubmit: () => void
  hintSubmitted: boolean
  hintsCount: number
  totalPlayers: number
}

function HintVariant({
  hintInput,
  onHintChange,
  onHintSubmit,
  hintSubmitted,
  hintsCount,
  totalPlayers,
}: HintVariantProps) {
  // Security V5: client-side whitespace guard (server also validates)
  const submitDisabled = !hintInput.trim() || hintSubmitted || /\s/.test(hintInput)

  return (
    <>
      <p aria-live="polite" className="panel-progress">
        {hintsCount}/{totalPlayers} dicas recebidas
      </p>
      <label className="panel-field">
        <span className="panel-label-text">Dica</span>
        <input
          type="text"
          maxLength={30}
          value={hintInput}
          onChange={(e) => onHintChange(e.target.value)}
          disabled={hintSubmitted}
          placeholder="Uma palavra..."
          className="panel-input"
          aria-label="Dica de uma palavra"
        />
      </label>
      <button
        type="button"
        onClick={onHintSubmit}
        disabled={submitDisabled}
        aria-disabled={submitDisabled ? 'true' : 'false'}
        className="panel-btn-primary"
      >
        {hintSubmitted ? 'Dica enviada' : 'Enviar dica'}
      </button>
    </>
  )
}

interface GuessVariantProps {
  players: Player[]
  myPlayerId: string
  hints: Record<string, string>
  guessTarget: string
  onGuessTargetChange: (v: string) => void
  guessInput: string
  onGuessInputChange: (v: string) => void
  onGuessSubmit: () => void
  onGuessSkip: () => void
  guessSubmitted: boolean
  guessIsCorrect: boolean | null
}

function GuessVariant({
  players,
  myPlayerId,
  hints,
  guessTarget,
  onGuessTargetChange,
  guessInput,
  onGuessInputChange,
  onGuessSubmit,
  onGuessSkip,
  guessSubmitted,
  guessIsCorrect,
}: GuessVariantProps) {
  const otherPlayers = players.filter((p) => p.player_id !== myPlayerId)
  const submitDisabled = guessTarget === '' || !guessInput.trim() || guessSubmitted

  return (
    <>
      <div className="panel-field">
        <span className="panel-label-text">Dicas dos jogadores:</span>
        <div className="hint-chips">
          {Object.entries(hints).length === 0 ? (
            <span className="panel-label-text">Aguardando jogadores</span>
          ) : (
            Object.entries(hints).map(([playerId, hintWord]) => (
              <span
                key={playerId}
                className={[
                  'hint-chip',
                  playerId === myPlayerId ? 'hint-chip--mine' : '',
                  !hintWord ? 'hint-chip--empty' : '',
                ]
                  .join(' ')
                  .trim()}
              >
                {playerName(players, playerId)}: {hintWord || '-'}
              </span>
            ))
          )}
        </div>
      </div>
      <label className="panel-field">
        <span className="panel-label-text">Adivinhar objeto de:</span>
        <select
          value={guessTarget}
          onChange={(e) => onGuessTargetChange(e.target.value)}
          disabled={guessSubmitted}
          className="panel-input"
        >
          <option value="">Selecione um jogador</option>
          {otherPlayers.map((p) => (
            <option key={p.player_id} value={p.player_id}>
              {p.player_name}
            </option>
          ))}
        </select>
      </label>
      <label className="panel-field">
        <span className="panel-label-text">Palpite</span>
        <input
          type="text"
          maxLength={50}
          value={guessInput}
          onChange={(e) => onGuessInputChange(e.target.value)}
          disabled={guessSubmitted}
          aria-label="Palpite"
          placeholder="Seu palpite..."
          className="panel-input"
        />
      </label>
      <div className="panel-btn-row">
        <button
          type="button"
          onClick={onGuessSubmit}
          disabled={submitDisabled}
          aria-disabled={submitDisabled ? 'true' : 'false'}
          className="panel-btn-primary panel-btn-primary--flex"
        >
          {guessSubmitted ? 'Palpite enviado' : 'Enviar palpite'}
        </button>
        <button
          type="button"
          onClick={onGuessSkip}
          disabled={guessSubmitted}
          aria-disabled={guessSubmitted ? 'true' : 'false'}
          className="panel-btn-skip"
        >
          Passar
        </button>
      </div>
      {guessSubmitted && (
        <p
          aria-live="polite"
          className={[
            'guess-result',
            guessIsCorrect === true ? 'guess-result--correct' : '',
            guessIsCorrect === false ? 'guess-result--incorrect' : '',
          ]
            .join(' ')
            .trim()}
        >
          {guessIsCorrect === true
            ? 'Correto!'
            : guessIsCorrect === false
              ? 'Errado.'
              : 'Aguardando resultado...'}
        </p>
      )}
    </>
  )
}

interface ExchangeVariantProps {
  players: Player[]
  exchangeRequest: ExchangeRequest | null
  myExchangeId: string | null
  exchangeStatus: string | null
  exchangeHintInput: string
  onExchangeHintChange: (v: string) => void
  onExchangeAccept: () => void
  onExchangeDecline: () => void
  onExchangeHintSubmit: () => void
  exchangeHintSubmitted: boolean
}

function ExchangeVariant({
  players,
  exchangeRequest,
  myExchangeId,
  exchangeStatus,
  exchangeHintInput,
  onExchangeHintChange,
  onExchangeAccept,
  onExchangeDecline,
  onExchangeHintSubmit,
  exchangeHintSubmitted,
}: ExchangeVariantProps) {
  const isRequester = myExchangeId !== null

  if (isRequester) {
    // Requester view: show status and hint field if accepted
    if (exchangeStatus === 'accepted') {
      return (
        <>
          <p className="phase-modal-status-text">Troca aceita! Envie sua dica privada.</p>
          <label className="panel-field">
            <span className="panel-label-text">Dica privada</span>
            <input
              type="text"
              maxLength={30}
              value={exchangeHintInput}
              onChange={(e) => onExchangeHintChange(e.target.value)}
              disabled={exchangeHintSubmitted}
              placeholder="Uma palavra..."
              className="panel-input"
              aria-label="Dica privada de troca"
            />
          </label>
          <button
            type="button"
            onClick={onExchangeHintSubmit}
            disabled={!exchangeHintInput.trim() || exchangeHintSubmitted}
            className="panel-btn-primary"
          >
            {exchangeHintSubmitted ? 'Dica enviada' : 'Enviar dica privada'}
          </button>
        </>
      )
    }
    return (
      <p className="phase-modal-status-text">Aguardando resposta...</p>
    )
  }

  if (!isRequester && exchangeRequest !== null) {
    // Recipient view: show Aceitar/Recusar buttons
    const requesterDisplayName = playerName(players, exchangeRequest.requester_id)
    return (
      <>
        <p className="phase-modal-status-text">
          {requesterDisplayName} quer trocar dicas com você.
        </p>
        <div className="panel-btn-row">
          <button
            type="button"
            onClick={onExchangeAccept}
            className="panel-btn-primary panel-btn-primary--flex"
          >
            Aceitar
          </button>
          <button
            type="button"
            onClick={onExchangeDecline}
            className="panel-btn-skip"
          >
            Recusar
          </button>
        </div>
        {exchangeStatus === 'accepted' && (
          <>
            <label className="panel-field">
              <span className="panel-label-text">Dica privada</span>
              <input
                type="text"
                maxLength={30}
                value={exchangeHintInput}
                onChange={(e) => onExchangeHintChange(e.target.value)}
                disabled={exchangeHintSubmitted}
                placeholder="Uma palavra..."
                className="panel-input"
                aria-label="Dica privada de troca"
              />
            </label>
            <button
              type="button"
              onClick={onExchangeHintSubmit}
              disabled={!exchangeHintInput.trim() || exchangeHintSubmitted}
              className="panel-btn-primary"
            >
              {exchangeHintSubmitted ? 'Dica enviada' : 'Enviar dica privada'}
            </button>
          </>
        )}
      </>
    )
  }

  // Neither requester nor recipient
  return (
    <p className="phase-modal-status-text">Aguardando fase de troca...</p>
  )
}

interface SpyVariantProps {
  spyTargets: string[]
  selectedSpyTarget: string
  onSpyTargetSelect: (id: string) => void
  onSpyAttempt: () => void
  spyAttempted: boolean
}

function SpyVariant({
  spyTargets,
  selectedSpyTarget,
  onSpyTargetSelect,
  onSpyAttempt,
  spyAttempted,
}: SpyVariantProps) {
  if (spyTargets.length === 0) {
    return (
      <p className="phase-modal-status-text">Nenhuma troca ativa no momento.</p>
    )
  }

  return (
    <>
      <ul className="phase-modal-spy-list">
        {spyTargets.map((id, index) => (
          <li
            key={id}
            className={[
              'phase-modal-spy-item',
              id === selectedSpyTarget ? 'phase-modal-spy-item--selected' : '',
            ]
              .join(' ')
              .trim()}
            onClick={() => onSpyTargetSelect(id)}
          >
            Troca {index + 1}
          </li>
        ))}
      </ul>
      <p className="phase-modal-risk-text">
        Atenção: se descoberto, você perde 10 pontos. Deseja continuar?
      </p>
      <button
        type="button"
        onClick={onSpyAttempt}
        disabled={!selectedSpyTarget || spyAttempted}
        className="panel-btn-skip"
      >
        Espiar
      </button>
    </>
  )
}

/* ─── Main component ─────────────────────────────────────────────────────── */

export default function PhaseModal(props: PhaseModalProps) {
  const {
    phase,
    players,
    myPlayerId,
    hintInput,
    onHintChange,
    onHintSubmit,
    hintSubmitted,
    hintsCount,
    totalPlayers,
    hints,
    guessTarget,
    onGuessTargetChange,
    guessInput,
    onGuessInputChange,
    onGuessSubmit,
    onGuessSkip,
    guessSubmitted,
    guessIsCorrect,
    exchangeRequest,
    myExchangeId,
    exchangeStatus,
    exchangeHintInput,
    onExchangeHintChange,
    onExchangeAccept,
    onExchangeDecline,
    onExchangeHintSubmit,
    exchangeHintSubmitted,
    spyTargets,
    selectedSpyTarget,
    onSpyTargetSelect,
    onSpyAttempt,
    spyAttempted,
  } = props

  // Return null for all non-action phases (SCORING_PHASE, ROUND_START, TURN_END, etc.)
  if (!ACTION_PHASES.includes(phase)) return null

  return (
    <div className="phase-modal-overlay">
      <div className="phase-modal-surface">
        <div className="phase-modal-header">
          <PhaseBadge phase={phase} />
          <h2 className="phase-modal-title">{PHASE_TITLES[phase]}</h2>
        </div>

        {phase === 'HINT_PHASE' && (
          <HintVariant
            hintInput={hintInput}
            onHintChange={onHintChange}
            onHintSubmit={onHintSubmit}
            hintSubmitted={hintSubmitted}
            hintsCount={hintsCount}
            totalPlayers={totalPlayers}
          />
        )}

        {phase === 'GUESS_PHASE' && (
          <GuessVariant
            players={players}
            myPlayerId={myPlayerId}
            hints={hints}
            guessTarget={guessTarget}
            onGuessTargetChange={onGuessTargetChange}
            guessInput={guessInput}
            onGuessInputChange={onGuessInputChange}
            onGuessSubmit={onGuessSubmit}
            onGuessSkip={onGuessSkip}
            guessSubmitted={guessSubmitted}
            guessIsCorrect={guessIsCorrect}
          />
        )}

        {phase === 'EXCHANGE_PHASE' && (
          <ExchangeVariant
            players={players}
            exchangeRequest={exchangeRequest}
            myExchangeId={myExchangeId}
            exchangeStatus={exchangeStatus}
            exchangeHintInput={exchangeHintInput}
            onExchangeHintChange={onExchangeHintChange}
            onExchangeAccept={onExchangeAccept}
            onExchangeDecline={onExchangeDecline}
            onExchangeHintSubmit={onExchangeHintSubmit}
            exchangeHintSubmitted={exchangeHintSubmitted}
          />
        )}

        {phase === 'SPY_PHASE' && (
          <SpyVariant
            spyTargets={spyTargets}
            selectedSpyTarget={selectedSpyTarget}
            onSpyTargetSelect={onSpyTargetSelect}
            onSpyAttempt={onSpyAttempt}
            spyAttempted={spyAttempted}
          />
        )}
      </div>
    </div>
  )
}
