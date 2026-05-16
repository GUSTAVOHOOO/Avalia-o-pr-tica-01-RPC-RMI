import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router'
import socket from '../socket'
import PhaseBadge from '../components/PhaseBadge'
import CountdownDisplay from '../components/CountdownDisplay'
import ChatPanel from '../components/ChatPanel'
import './GameScreen.css'

interface ObjectAssignedPayload {
  image_url: string
  object_name: string
}

interface HintReceivedPayload {
  hints_count: number
  total_players: number
}

interface GuessResultPayload {
  guesser_id: string
  target_player_id: string
  is_correct: boolean
}

interface ScoreEntry {
  player_id: string
  player_name: string
  turn_delta: number
  total: number
}

interface ScoreUpdatedPayload {
  turn_number: number
  scores: ScoreEntry[]
}

interface Player {
  player_id: string
  player_name: string
  is_host: boolean
}

interface PhaseChangedPayload {
  phase: string
  remaining_seconds: number
  current_turn: number
  max_turns: number
  room_code: string
  hints?: Record<string, string>
}

interface JoinRoomPayload {
  error?: string
  status?: string
  phase?: string
  remaining_seconds?: number
  current_turn?: number
  max_turns?: number
  players?: Player[]
  object_assignment?: ObjectAssignedPayload | null
}

interface ChatMessage {
  player_id: string
  player_name: string
  message: string
  timestamp: number
}

interface VoteStartedPayload {
  room_code: string
  duration_seconds: number
  player_count: number
}

const passiveStatus: Record<string, string> = {
  ROUND_START: 'Aguardando proxima fase...',
  EXCHANGE_PHASE: 'Aguardando proxima fase...',
  SPY_PHASE: 'Aguardando proxima fase...',
  TURN_END: 'Aguardando proxima fase...',
  WAITING: 'Aguardando proxima fase...',
}

function readPlayersFromStorage(): Player[] {
  try {
    return JSON.parse(localStorage.getItem('players') ?? '[]') as Player[]
  } catch {
    return []
  }
}

function playerName(players: Player[], playerId: string) {
  return players.find((p) => p.player_id === playerId)?.player_name ?? playerId
}

function formatDelta(delta: number) {
  if (delta > 0) return `+${delta} pts`
  return `${delta} pts`
}

/* ─── SecretImagePanel ────────────────────────────────────────────────────── */
function SecretImagePanel({ assignment }: { assignment: ObjectAssignedPayload | null }) {
  return (
    <section className="secret-image-panel">
      {assignment ? (
        <img
          src={assignment.image_url}
          alt={`Imagem do objeto: ${assignment.object_name}`}
          className="secret-image-panel__img"
        />
      ) : (
        <div className="secret-image-panel__placeholder">
          Aguardando imagem...
        </div>
      )}
      <span className="secret-image-panel__label">Seu objeto secreto</span>
      {assignment && (
        <span className="secret-image-panel__name">
          {assignment.object_name}
        </span>
      )}
    </section>
  )
}

/* ─── GameScreen ──────────────────────────────────────────────────────────── */
export default function GameScreen() {
  const { roomCode } = useParams<{ roomCode: string }>()
  const navigate = useNavigate()
  const myPlayerId = localStorage.getItem('player_id') ?? ''

  const [currentPhase, setCurrentPhase] = useState<string | null>(null)
  const [remainingSeconds, setRemainingSeconds] = useState(0)
  const [currentTurn, setCurrentTurn] = useState(1)
  const [maxTurns, setMaxTurns] = useState(1)
  const [gameEnded, setGameEnded] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [players, setPlayers] = useState<Player[]>(readPlayersFromStorage)
  const [myObjectAssignment, setMyObjectAssignment] = useState<ObjectAssignedPayload | null>(null)
  const [hintsCount, setHintsCount] = useState(0)
  const [totalPlayers, setTotalPlayers] = useState(0)
  const [myHintSubmitted, setMyHintSubmitted] = useState(false)
  const [hintInput, setHintInput] = useState('')
  const [hints, setHints] = useState<Record<string, string>>({})
  const [myGuessSubmitted, setMyGuessSubmitted] = useState(false)
  const [guessTarget, setGuessTarget] = useState('')
  const [guessInput, setGuessInput] = useState('')
  const [guessIsCorrect, setGuessIsCorrect] = useState<boolean | null>(null)
  const [scores, setScores] = useState<ScoreEntry[]>([])
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [playerLeftMsg, setPlayerLeftMsg] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!socket.connected) socket.connect()

    const applyPhase = (data: PhaseChangedPayload) => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }

      setGameEnded(false)
      setCurrentPhase(data.phase)
      setRemainingSeconds(data.remaining_seconds)
      setCurrentTurn(data.current_turn)
      setMaxTurns(data.max_turns)

      if (data.phase === 'HINT_PHASE') {
        setMyHintSubmitted(false)
        setHintInput('')
        setHintsCount(0)
        setMyGuessSubmitted(false)
        setGuessTarget('')
        setGuessInput('')
        setGuessIsCorrect(null)
        setScores([])
      }
      if (data.phase === 'GUESS_PHASE' && data.hints) {
        setHints(data.hints)
      }

      let secs = data.remaining_seconds
      intervalRef.current = setInterval(() => {
        secs = Math.max(0, secs - 1)
        setRemainingSeconds(secs)
      }, 1000)
    }

    const storedPlayerId = localStorage.getItem('player_id') ?? ''

    const handleReconnectOrJoin = (data: JoinRoomPayload) => {
      if (data?.error) {
        setConnectionError(String(data.error))
        return
      }

      setConnectionError(null)
      if (data?.players) {
        setPlayers(data.players)
        localStorage.setItem('players', JSON.stringify(data.players))
        setTotalPlayers(data.players.length)
      }
      if (data?.object_assignment) {
        setMyObjectAssignment(data.object_assignment)
      }
      if (data?.status === 'ENDED') {
        navigate(`/postgame/${roomCode}`)
        return
      }

      if (data?.phase) {
        applyPhase({
          phase: data.phase,
          remaining_seconds: data.remaining_seconds ?? 0,
          current_turn: data.current_turn ?? 1,
          max_turns: data.max_turns ?? 1,
          room_code: roomCode ?? '',
        })
      }
    }

    if (storedPlayerId && roomCode) {
      socket.emit('reconnect_game', { player_id: storedPlayerId, room_code: roomCode }, handleReconnectOrJoin)
    } else {
      socket.emit('join_room', { room_code: roomCode, player_id: myPlayerId }, handleReconnectOrJoin)
    }

    const handlePhaseChanged = (data: PhaseChangedPayload) => {
      setConnectionError(null)
      applyPhase(data)
    }
    const handleObjectAssigned = (data: ObjectAssignedPayload) => setMyObjectAssignment(data)
    const handleHintReceived = (data: HintReceivedPayload) => {
      setHintsCount(data.hints_count)
      setTotalPlayers(data.total_players)
    }
    const handleGuessResult = (data: GuessResultPayload) => {
      if (data.guesser_id === myPlayerId) setGuessIsCorrect(data.is_correct)
    }
    const handleScoreUpdated = (data: ScoreUpdatedPayload) => setScores(data.scores)
    const handleGameEnded = (data: { final_scores?: unknown[] }) => {
      // TurnMachine broadcasts game_ended (no final_scores) before _start_vote().
      // Ignore that intermediate broadcast — vote_started handles navigation.
      // Only navigate here if this is _resolve_vote's broadcast (has final_scores).
      if (!data?.final_scores) return
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      navigate(`/postgame/${roomCode}`)
    }
    const handlePlayerLeft = (data: { player_id: string; player_name: string }) => {
      setPlayers((prev) => prev.filter((p) => p.player_id !== data.player_id))
      setPlayerLeftMsg(`${data.player_name} saiu da partida`)
      setTimeout(() => setPlayerLeftMsg(null), 4000)
    }
    const handleGameRestarting = () => {
      navigate(`/game/${roomCode}`)
    }
    const handleChatMessage = (data: ChatMessage) => {
      setChatMessages((prev) => [...prev, data])
    }
    const handleVoteStarted = (data: VoteStartedPayload) => {
      navigate(`/postgame/${roomCode}`, {
        state: { voteActive: true, durationSeconds: data.duration_seconds, playerCount: data.player_count }
      })
    }

    socket.on('phase_changed', handlePhaseChanged)
    socket.on('object_assigned', handleObjectAssigned)
    socket.on('hint_received', handleHintReceived)
    socket.on('guess_result', handleGuessResult)
    socket.on('score_updated', handleScoreUpdated)
    socket.on('game_ended', handleGameEnded)
    socket.on('player_left', handlePlayerLeft)
    socket.on('game_restarting', handleGameRestarting)
    socket.on('chat_message', handleChatMessage)
    socket.on('vote_started', handleVoteStarted)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      socket.off('phase_changed', handlePhaseChanged)
      socket.off('object_assigned', handleObjectAssigned)
      socket.off('hint_received', handleHintReceived)
      socket.off('guess_result', handleGuessResult)
      socket.off('score_updated', handleScoreUpdated)
      socket.off('game_ended', handleGameEnded)
      socket.off('player_left', handlePlayerLeft)
      socket.off('game_restarting', handleGameRestarting)
      socket.off('chat_message', handleChatMessage)
      socket.off('vote_started', handleVoteStarted)
    }
  }, [roomCode, myPlayerId, navigate])

  const otherPlayers = players.filter((p) => p.player_id !== myPlayerId)
  const canSubmitHint = hintInput.trim() !== '' && !myHintSubmitted
  const canSubmitGuess = guessTarget !== '' && guessInput.trim() !== '' && !myGuessSubmitted

  function submitHint() {
    if (!canSubmitHint) return
    socket.emit('submit_hint', { hint_word: hintInput }, () => undefined)
    setMyHintSubmitted(true)
  }

  function submitGuess() {
    if (!canSubmitGuess) return
    socket.emit('submit_guess', { target_player_id: guessTarget, guess_word: guessInput }, () => undefined)
    setMyGuessSubmitted(true)
    setGuessIsCorrect(null)
  }

  function skipGuess() {
    if (myGuessSubmitted) return
    socket.emit('skip_guess', {}, () => undefined)
    setMyGuessSubmitted(true)
  }

  function sendChatMessage(msg: string) {
    socket.emit('send_chat', { message: msg }, () => undefined)
  }

  /* ─── Phase panels ──────────────────────────────────────────────────────── */
  const renderPhasePanel = () => {
    if (currentPhase === 'HINT_PHASE') {
      return (
        <>
          <SecretImagePanel assignment={myObjectAssignment} />
          <section className="phase-panel phase-panel--hint">
            <h2 className="phase-panel__title">Fase de Dicas</h2>
            <p aria-live="polite" className="panel-progress">
              {hintsCount}/{totalPlayers} dicas recebidas
            </p>
            <label className="panel-field">
              <span className="panel-label-text">Dica</span>
              <input
                type="text"
                maxLength={30}
                value={hintInput}
                onChange={(e) => setHintInput(e.target.value)}
                disabled={myHintSubmitted}
                aria-label="Dica de uma palavra"
                placeholder="Uma palavra..."
                className="panel-input"
              />
            </label>
            <button
              type="button"
              onClick={submitHint}
              disabled={!canSubmitHint}
              aria-disabled={!canSubmitHint ? 'true' : 'false'}
              className="panel-btn-primary"
            >
              {myHintSubmitted ? 'Dica enviada' : 'Enviar Dica'}
            </button>
          </section>
        </>
      )
    }

    if (currentPhase === 'GUESS_PHASE') {
      return (
        <>
          <SecretImagePanel assignment={myObjectAssignment} />
          <section className="phase-panel phase-panel--guess">
            <h2 className="phase-panel__title">Fase de Palpites</h2>
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
                      ].join(' ').trim()}
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
                onChange={(e) => setGuessTarget(e.target.value)}
                disabled={myGuessSubmitted}
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
                onChange={(e) => setGuessInput(e.target.value)}
                disabled={myGuessSubmitted}
                aria-label="Palpite"
                placeholder="Sua palavra..."
                className="panel-input"
              />
            </label>
            <div className="panel-btn-row">
              <button
                type="button"
                onClick={submitGuess}
                disabled={!canSubmitGuess}
                aria-disabled={!canSubmitGuess ? 'true' : 'false'}
                className="panel-btn-primary panel-btn-primary--flex"
              >
                {myGuessSubmitted ? 'Palpite enviado' : 'Enviar Palpite'}
              </button>
              <button
                type="button"
                onClick={skipGuess}
                disabled={myGuessSubmitted}
                aria-disabled={myGuessSubmitted ? 'true' : 'false'}
                className="panel-btn-skip"
              >
                Passar
              </button>
            </div>
            {myGuessSubmitted && (
              <p
                aria-live="polite"
                className={[
                  'guess-result',
                  guessIsCorrect === true ? 'guess-result--correct' : '',
                  guessIsCorrect === false ? 'guess-result--incorrect' : '',
                ].join(' ').trim()}
              >
                {guessIsCorrect === true
                  ? 'Correto!'
                  : guessIsCorrect === false
                    ? 'Errado.'
                    : 'Aguardando resultado...'}
              </p>
            )}
          </section>
        </>
      )
    }

    if (currentPhase === 'SCORING_PHASE') {
      return (
        <section className="phase-panel phase-panel--scoring">
          <h2 className="phase-panel__title">Pontuacao do Turno</h2>
          {scores.length === 0 ? (
            <p className="score-calculating">Calculando pontuacao...</p>
          ) : (
            <div className="score-list">
              {scores.map((score) => (
                <div
                  key={score.player_id}
                  className={[
                    'score-row',
                    score.player_id === myPlayerId ? 'score-row--mine' : '',
                  ].join(' ').trim()}
                >
                  <span className="score-row__name">{score.player_name}</span>
                  <span
                    className={[
                      'score-row__delta',
                      score.turn_delta > 0 ? 'score-row__delta--positive' : '',
                      score.turn_delta < 0 ? 'score-row__delta--negative' : '',
                    ].join(' ').trim()}
                  >
                    {formatDelta(score.turn_delta)}
                  </span>
                  <span className="score-row__total">Total: {score.total}</span>
                </div>
              ))}
            </div>
          )}
        </section>
      )
    }

    return (
      <p className="game-screen__status">
        {passiveStatus[currentPhase ?? ''] ?? 'Aguardando proxima fase...'}
      </p>
    )
  }

  /* ─── Main render ───────────────────────────────────────────────────────── */
  return (
    <div className="game-screen">
      {playerLeftMsg && (
        <div className="player-left-toast">
          <span className="player-left-toast__text">{playerLeftMsg}</span>
        </div>
      )}
      <div className="game-screen__header">
        <div>{currentPhase !== null && <PhaseBadge phase={currentPhase} />}</div>

        <div>
          {!gameEnded && currentPhase !== null && (
            <CountdownDisplay seconds={remainingSeconds} />
          )}
        </div>

        <span
          className="game-screen__turn"
          aria-label={`Turno ${currentTurn} de ${maxTurns}`}
        >
          Turno {currentTurn} de {maxTurns}
        </span>
      </div>

      <div className="game-screen__body">
        <div className="game-screen__content">
          {gameEnded ? (
            <p className="game-screen__status">
              Jogo encerrado. Aguardando tela de resultados...
            </p>
          ) : connectionError !== null ? (
            <p className="game-screen__status game-screen__status--error">
              {connectionError}
            </p>
          ) : currentPhase === null ? (
            <p className="game-screen__status">Conectando...</p>
          ) : (
            renderPhasePanel()
          )}
          <ChatPanel
            messages={chatMessages}
            myPlayerId={myPlayerId}
            onSend={sendChatMessage}
          />
        </div>
      </div>
    </div>
  )
}
