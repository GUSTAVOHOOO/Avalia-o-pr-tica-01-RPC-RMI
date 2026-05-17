import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router'
import socket from '../socket'
import PhaseBadge from '../components/PhaseBadge'
import CountdownDisplay from '../components/CountdownDisplay'
import ChatPanel from '../components/ChatPanel'
import PhaseModal from '../components/PhaseModal'
import ReconnectionBanner from '../components/ReconnectionBanner'
import ScoreDeltaToast from '../components/ScoreDeltaToast'
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
  spy_targets?: string[]
}

interface PhaseTimerShortenedPayload {
  phase: string
  remaining_seconds: number
  current_turn: number
  max_turns: number
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

/* ─── Exchange/SPY types ──────────────────────────────────────────────────── */
interface ExchangeRequest { exchange_id: string; requester_id: string }
interface ExchangeHintPayload { from_player_id: string; hint_word: string }
interface SpyHintPayload { from_player_id: string; hint_word: string }
interface DeltaToast { id: string; playerName: string; delta: number }

const passiveStatus: Record<string, string> = {
  ROUND_START: 'Aguardando proxima fase...',
  EXCHANGE_PHASE: 'Aguardando proxima fase...',
  SPY_PHASE: 'Aguardando proxima fase...',
  TURN_END: 'Aguardando proxima fase...',
  WAITING: 'Aguardando proxima fase...',
}

const ACTION_PHASES = ['HINT_PHASE', 'GUESS_PHASE', 'EXCHANGE_PHASE', 'SPY_PHASE']

function readPlayersFromStorage(): Player[] {
  try {
    return JSON.parse(localStorage.getItem('players') ?? '[]') as Player[]
  } catch {
    return []
  }
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

  // Exchange/SPY state
  const [exchangeRequest, setExchangeRequest] = useState<ExchangeRequest | null>(null)
  const [myExchangeId, setMyExchangeId] = useState<string | null>(null)
  const [exchangeStatus, setExchangeStatus] = useState<string | null>(null)
  const [exchangeHintInput, setExchangeHintInput] = useState('')
  const [exchangeHintSubmitted, setExchangeHintSubmitted] = useState(false)
  const [exchangeTarget, setExchangeTarget] = useState('')
  const [exchangeSkipped, setExchangeSkipped] = useState(false)
  const [exchangeReceivedHints, setExchangeReceivedHints] = useState<ExchangeHintPayload[]>([])
  const [selectedSpyTarget, setSelectedSpyTarget] = useState('')
  const [spyTargets, setSpyTargets] = useState<string[]>([])
  const [spyAttempted, setSpyAttempted] = useState(false)
  const [spyResult, setSpyResult] = useState<'success' | 'discovered' | null>(null)
  const [spyReceivedHints, setSpyReceivedHints] = useState<SpyHintPayload[]>([])
  // Delta toasts
  const [deltaToasts, setDeltaToasts] = useState<DeltaToast[]>([])
  // Banner
  const [bannerVisible, setBannerVisible] = useState(false)

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
        // Reset exchange/spy state on new turn
        setExchangeRequest(null)
        setMyExchangeId(null)
        setExchangeStatus(null)
        setExchangeHintInput('')
        setExchangeHintSubmitted(false)
        setExchangeTarget('')
        setExchangeSkipped(false)
        setExchangeReceivedHints([])
        setSelectedSpyTarget('')
        setSpyAttempted(false)
        setSpyResult(null)
        setSpyReceivedHints([])
        setDeltaToasts([])
      }
      if (data.phase === 'GUESS_PHASE' && data.hints) {
        setHints(data.hints)
      }
      if (data.phase === 'SPY_PHASE' && data.spy_targets) {
        setSpyTargets(data.spy_targets)
        setSelectedSpyTarget('')
        setSpyAttempted(false)
        setSpyResult(null)
        setSpyReceivedHints([])
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
    const handlePhaseTimerShortened = (data: PhaseTimerShortenedPayload) => {
      setConnectionError(null)
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }

      setCurrentPhase(data.phase)
      setRemainingSeconds(data.remaining_seconds)
      setCurrentTurn(data.current_turn)
      setMaxTurns(data.max_turns)

      let secs = data.remaining_seconds
      intervalRef.current = setInterval(() => {
        secs = Math.max(0, secs - 1)
        setRemainingSeconds(secs)
      }, 1000)
    }
    const handleObjectAssigned = (data: ObjectAssignedPayload) => setMyObjectAssignment(data)
    const handleHintReceived = (data: HintReceivedPayload) => {
      setHintsCount(data.hints_count)
      setTotalPlayers(data.total_players)
    }
    const handleGuessResult = (data: GuessResultPayload) => {
      if (data.guesser_id === myPlayerId) setGuessIsCorrect(data.is_correct)
    }
    const handleScoreUpdated = (data: ScoreUpdatedPayload) => {
      setScores(data.scores)
      const newToasts = data.scores
        .filter((s) => s.turn_delta !== 0)
        .map((s) => ({
          id: `${s.player_id}-${Date.now()}`,
          playerName: s.player_name,
          delta: s.turn_delta,
        }))
      setDeltaToasts((prev) => [...prev, ...newToasts])
    }
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
    // Sync full player list whenever player_joined fires — covers race where
    // GameScreen mounted before localStorage was fully written in Lobby (BUG-GUESS-01)
    const handlePlayerJoined = (data: { players?: Player[] }) => {
      if (data?.players && data.players.length > 0) {
        setPlayers(data.players)
        setTotalPlayers(data.players.length)
        localStorage.setItem('players', JSON.stringify(data.players))
      }
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

    // Exchange/SPY handlers
    const handleExchangeRequested = (data: { exchange_id: string; requester_id: string }) => {
      setExchangeRequest({ exchange_id: data.exchange_id, requester_id: data.requester_id })
    }
    const handleExchangeAccepted = () => {
      setExchangeStatus('accepted')
    }
    const handleExchangeRejected = () => {
      setMyExchangeId(null)
      setExchangeStatus(null)
    }
    const handleExchangeHints = (data: ExchangeHintPayload) => {
      setExchangeHintSubmitted(true)
      setExchangeReceivedHints((prev) => [...prev, {
        from_player_id: data.from_player_id,
        hint_word: data.hint_word,
      }])
    }
    const handleSpySuccess = (data: { hints?: SpyHintPayload[] }) => {
      setSpyAttempted(true)
      setSpyResult('success')
      setSpyReceivedHints(data.hints ?? [])
    }
    const handleSpyDiscovered = () => {
      setSpyAttempted(true)
      setSpyResult('discovered')
    }

    socket.on('phase_changed', handlePhaseChanged)
    socket.on('phase_timer_shortened', handlePhaseTimerShortened)
    socket.on('object_assigned', handleObjectAssigned)
    socket.on('hint_received', handleHintReceived)
    socket.on('guess_result', handleGuessResult)
    socket.on('score_updated', handleScoreUpdated)
    socket.on('game_ended', handleGameEnded)
    socket.on('player_left', handlePlayerLeft)
    socket.on('player_joined', handlePlayerJoined)
    socket.on('game_restarting', handleGameRestarting)
    socket.on('chat_message', handleChatMessage)
    socket.on('vote_started', handleVoteStarted)
    socket.on('exchange_requested', handleExchangeRequested)
    socket.on('exchange_accepted', handleExchangeAccepted)
    socket.on('exchange_rejected', handleExchangeRejected)
    socket.on('exchange_hints', handleExchangeHints)
    socket.on('spy_success', handleSpySuccess)
    socket.on('spy_discovered', handleSpyDiscovered)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      socket.off('phase_changed', handlePhaseChanged)
      socket.off('phase_timer_shortened', handlePhaseTimerShortened)
      socket.off('object_assigned', handleObjectAssigned)
      socket.off('hint_received', handleHintReceived)
      socket.off('guess_result', handleGuessResult)
      socket.off('score_updated', handleScoreUpdated)
      socket.off('game_ended', handleGameEnded)
      socket.off('player_left', handlePlayerLeft)
      socket.off('player_joined', handlePlayerJoined)
      socket.off('game_restarting', handleGameRestarting)
      socket.off('chat_message', handleChatMessage)
      socket.off('vote_started', handleVoteStarted)
      socket.off('exchange_requested', handleExchangeRequested)
      socket.off('exchange_accepted', handleExchangeAccepted)
      socket.off('exchange_rejected', handleExchangeRejected)
      socket.off('exchange_hints', handleExchangeHints)
      socket.off('spy_success', handleSpySuccess)
      socket.off('spy_discovered', handleSpyDiscovered)
    }
  }, [roomCode, myPlayerId, navigate])

  function submitHint() {
    const canSubmit = hintInput.trim() !== '' && !myHintSubmitted
    if (!canSubmit) return
    socket.emit('submit_hint', { hint_word: hintInput }, () => undefined)
    setMyHintSubmitted(true)
  }

  function submitGuess() {
    const canSubmit = guessTarget !== '' && guessInput.trim() !== '' && !myGuessSubmitted
    if (!canSubmit) return
    socket.emit('submit_guess', { target_player_id: guessTarget, guess_word: guessInput }, () => undefined)
    setMyGuessSubmitted(true)
    setGuessIsCorrect(null)
  }

  function skipGuess() {
    if (myGuessSubmitted) return
    socket.emit('skip_guess', {}, () => undefined)
    setMyGuessSubmitted(true)
  }

  function requestExchange() {
    if (!exchangeTarget || exchangeSkipped) return
    socket.emit('request_exchange', { target_player_id: exchangeTarget }, (result: { exchange_id?: string; error?: string } | undefined) => {
      if (!result?.exchange_id || result.error) return
      setMyExchangeId(result.exchange_id)
      setExchangeTarget('')
      setExchangeStatus('pending')
      setExchangeReceivedHints([])
    })
  }

  function skipExchange() {
    if (exchangeSkipped || myExchangeId || exchangeRequest) return
    socket.emit('skip_exchange', {}, () => undefined)
    setExchangeSkipped(true)
    setExchangeTarget('')
  }

  function respondExchange(accept: boolean) {
    if (!exchangeRequest) return
    socket.emit('respond_exchange', { exchange_id: exchangeRequest.exchange_id, accept }, () => undefined)
    if (!accept) setExchangeRequest(null)
    else {
      setExchangeStatus('accepted')
      setExchangeReceivedHints([])
    }
  }

  function submitExchangeHint() {
    const activeExchangeId = exchangeRequest?.exchange_id ?? myExchangeId
    if (!activeExchangeId || exchangeHintSubmitted) return
    socket.emit('submit_exchange_hint', { exchange_id: activeExchangeId, hint_word: exchangeHintInput }, () => undefined)
    setExchangeHintSubmitted(true)
  }

  function attemptSpy() {
    if (!selectedSpyTarget || spyAttempted) return
    socket.emit('attempt_spy', { exchange_id: selectedSpyTarget }, () => undefined)
    setSpyAttempted(true)
    setSpyResult(null)
    setSpyReceivedHints([])
  }

  const removeToast = (id: string) => setDeltaToasts((prev) => prev.filter((t) => t.id !== id))

  function sendChatMessage(msg: string) {
    socket.emit('send_chat', { message: msg }, () => undefined)
  }

  /* ─── Main render ───────────────────────────────────────────────────────── */
  return (
    <div className={`game-screen${bannerVisible ? ' game-screen--banner-visible' : ''}`}>
      <ReconnectionBanner onStateChange={setBannerVisible} />
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
        <span className="game-screen__turn" aria-label={`Turno ${currentTurn} de ${maxTurns}`}>
          Turno {currentTurn} de {maxTurns}
        </span>
      </div>

      <div className="game-screen__body">
        {/* ─── Main column ─── */}
        <div className="game-screen__main">
          {gameEnded ? (
            <p className="game-screen__status">Jogo encerrado. Aguardando tela de resultados...</p>
          ) : connectionError !== null ? (
            <p className="game-screen__status game-screen__status--error">{connectionError}</p>
          ) : currentPhase === null ? (
            <p className="game-screen__status">Conectando...</p>
          ) : (
            <>
              {/* Secret image — always visible during action phases */}
              {ACTION_PHASES.includes(currentPhase) && (
                <SecretImagePanel assignment={myObjectAssignment} />
              )}

              {/* Phase action panel — inline card, no overlay; key triggers fade on phase change */}
              <div key={currentPhase} className="phase-fade-in phase-panel--relative">
                <PhaseModal
                  phase={currentPhase}
                  players={players}
                  myPlayerId={myPlayerId}
                  hintInput={hintInput}
                  onHintChange={setHintInput}
                  onHintSubmit={submitHint}
                  hintSubmitted={myHintSubmitted}
                  hintsCount={hintsCount}
                  totalPlayers={totalPlayers}
                  hints={hints}
                  guessTarget={guessTarget}
                  onGuessTargetChange={setGuessTarget}
                  guessInput={guessInput}
                  onGuessInputChange={setGuessInput}
                  onGuessSubmit={submitGuess}
                  onGuessSkip={skipGuess}
                  guessSubmitted={myGuessSubmitted}
                  guessIsCorrect={guessIsCorrect}
                  exchangeRequest={exchangeRequest}
                  myExchangeId={myExchangeId}
                  exchangeStatus={exchangeStatus}
                  exchangeHintInput={exchangeHintInput}
                  onExchangeHintChange={setExchangeHintInput}
                  onExchangeAccept={() => respondExchange(true)}
                  onExchangeDecline={() => respondExchange(false)}
                  onExchangeHintSubmit={submitExchangeHint}
                  exchangeHintSubmitted={exchangeHintSubmitted}
                  exchangeTarget={exchangeTarget}
                  onExchangeTargetChange={setExchangeTarget}
                  onExchangeRequest={requestExchange}
                  onExchangeSkip={skipExchange}
                  exchangeSkipped={exchangeSkipped}
                  exchangeReceivedHints={exchangeReceivedHints}
                  spyTargets={spyTargets}
                  selectedSpyTarget={selectedSpyTarget}
                  onSpyTargetSelect={setSelectedSpyTarget}
                  onSpyAttempt={attemptSpy}
                  spyAttempted={spyAttempted}
                  spyResult={spyResult}
                  spyReceivedHints={spyReceivedHints}
                />
                {deltaToasts.map((t) => (
                  <ScoreDeltaToast key={t.id} id={t.id} delta={t.delta} playerName={t.playerName} onDone={removeToast} />
                ))}
              </div>

              {/* Scoring phase */}
              {currentPhase === 'SCORING_PHASE' && (
                <section key="scoring" className="phase-panel phase-panel--scoring phase-fade-in phase-panel--relative">
                  <h2 className="phase-panel__title">Pontuação do Turno</h2>
                  {deltaToasts.map((t) => (
                    <ScoreDeltaToast key={t.id} id={t.id} delta={t.delta} playerName={t.playerName} onDone={removeToast} />
                  ))}
                  {scores.length === 0 ? (
                    <p className="score-calculating">Calculando pontuação...</p>
                  ) : (
                    <div className="score-list">
                      {scores.map((score) => (
                        <div
                          key={score.player_id}
                          className={['score-row', score.player_id === myPlayerId ? 'score-row--mine' : ''].join(' ').trim()}
                        >
                          <span className="score-row__name">{score.player_name}</span>
                          <span className={['score-row__delta', score.turn_delta > 0 ? 'score-row__delta--positive' : '', score.turn_delta < 0 ? 'score-row__delta--negative' : ''].join(' ').trim()}>
                            {formatDelta(score.turn_delta)}
                          </span>
                          <span className="score-row__total">Total: {score.total}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </section>
              )}

              {/* Passive status */}
              {!ACTION_PHASES.includes(currentPhase) && currentPhase !== 'SCORING_PHASE' && (
                <p className="game-screen__status phase-fade-in">
                  {passiveStatus[currentPhase] ?? 'Aguardando próxima fase...'}
                </p>
              )}
            </>
          )}
        </div>

        {/* ─── Chat sidebar ─── */}
        <aside className="game-screen__sidebar">
          <ChatPanel
            messages={chatMessages}
            myPlayerId={myPlayerId}
            onSend={sendChatMessage}
          />
        </aside>
      </div>
    </div>
  )
}
