import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router'
import socket from '../socket'
import './PostGame.css'

interface ScoreEntry {
  player_id: string
  player_name: string
  total: number
}

interface TurnScoreEntry {
  turn: number
  scores: Record<string, number>
}

interface VoteStartedPayload {
  room_code: string
  duration_seconds: number
  player_count: number
}

interface VoteUpdatePayload {
  room_code: string
  yes_count: number
  votes_cast: number
  total: number
}

function voteBarColor(secondsLeft: number): string {
  if (secondsLeft <= 5) return '#ef4444'  // destructive
  if (secondsLeft <= 10) return '#eab308' // warning
  return '#6366f1'                         // accent
}

export default function PostGame() {
  const { roomCode } = useParams<{ roomCode: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const navState = location.state as { voteActive?: boolean; durationSeconds?: number; playerCount?: number } | null
  const myPlayerId = localStorage.getItem('player_id') ?? ''

  // Score data — may arrive via game_ended (which fires after vote_started navigate)
  const [finalScores, setFinalScores] = useState<ScoreEntry[]>([])
  const [turnHistory, setTurnHistory] = useState<TurnScoreEntry[]>([])

  // Vote state — initialize from nav state so vote UI shows immediately on mount
  const [voteActive, setVoteActive] = useState(navState?.voteActive ?? false)
  const [voteSecondsLeft, setVoteSecondsLeft] = useState(navState?.durationSeconds ?? 30)
  const [myVoteSubmitted, setMyVoteSubmitted] = useState(false)
  const [yesCount, setYesCount] = useState(0)
  const [votesCast, setVotesCast] = useState(0)
  const [totalPlayers, setTotalPlayers] = useState(navState?.playerCount ?? 0)

  const [voteResult, setVoteResult] = useState<'restarting' | 'ended' | null>(null)
  const [redirectCountdown, setRedirectCountdown] = useState(10)

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const redirectIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // On mount: start countdown from nav state OR sync via join_room if no nav state
  useEffect(() => {
    function startCountdown(secs: number) {
      if (intervalRef.current) clearInterval(intervalRef.current)
      let remaining = secs
      intervalRef.current = setInterval(() => {
        remaining = Math.max(0, remaining - 1)
        setVoteSecondsLeft(remaining)
        if (remaining === 0 && intervalRef.current) {
          clearInterval(intervalRef.current)
          intervalRef.current = null
        }
      }, 1000)
    }

    if (navState?.voteActive) {
      startCountdown(navState.durationSeconds ?? 30)
    } else if (roomCode && myPlayerId) {
      // No nav state — re-sync from server (reconnect / direct URL open)
      socket.emit(
        'join_room',
        { room_code: roomCode, player_id: myPlayerId },
        (resp: Record<string, unknown>) => {
          if (resp?.vote_active) {
            const secs = typeof resp.vote_seconds_remaining === 'number' ? resp.vote_seconds_remaining : 30
            const count = typeof resp.vote_player_count === 'number' ? resp.vote_player_count : 0
            setVoteActive(true)
            setVoteSecondsLeft(secs)
            setTotalPlayers(count)
            startCountdown(secs)
          }
        },
      )
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, []) // runs once on mount

  useEffect(() => {
    if (!socket.connected) socket.connect()

    const handleVoteStarted = (data: VoteStartedPayload) => {
      setVoteActive(true)
      setVoteSecondsLeft(data.duration_seconds)
      setTotalPlayers(data.player_count)

      // Start countdown
      let secs = data.duration_seconds
      if (intervalRef.current) clearInterval(intervalRef.current)
      intervalRef.current = setInterval(() => {
        secs = Math.max(0, secs - 1)
        setVoteSecondsLeft(secs)
        if (secs === 0 && intervalRef.current) {
          clearInterval(intervalRef.current)
          intervalRef.current = null
        }
      }, 1000)
    }

    const handleVoteUpdate = (data: VoteUpdatePayload) => {
      setYesCount(data.yes_count)
      setVotesCast(data.votes_cast)
      setTotalPlayers(data.total)
    }

    const handleGameRestarting = () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      setVoteResult('restarting')
      setTimeout(() => {
        navigate(`/game/${roomCode}`)
      }, 1500)
    }

    const handleGameEnded = (data: {
      final_scores?: ScoreEntry[]
      turn_score_history?: TurnScoreEntry[]
    }) => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      if (data.final_scores) {
        // Sort descending by total
        const sorted = [...data.final_scores].sort((a, b) => b.total - a.total)
        setFinalScores(sorted)
      }
      if (data.turn_score_history) {
        setTurnHistory(data.turn_score_history)
      }
      setVoteActive(false)
      setVoteResult('ended')

      // 10s redirect countdown then navigate to landing
      let count = 10
      setRedirectCountdown(count)
      if (redirectIntervalRef.current) clearInterval(redirectIntervalRef.current)
      redirectIntervalRef.current = setInterval(() => {
        count -= 1
        setRedirectCountdown(count)
        if (count <= 0) {
          if (redirectIntervalRef.current) {
            clearInterval(redirectIntervalRef.current)
            redirectIntervalRef.current = null
          }
          navigate('/')
        }
      }, 1000)
    }

    socket.on('vote_started', handleVoteStarted)
    socket.on('vote_update', handleVoteUpdate)
    socket.on('game_restarting', handleGameRestarting)
    socket.on('game_ended', handleGameEnded)

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
      if (redirectIntervalRef.current) clearInterval(redirectIntervalRef.current)
      socket.off('vote_started', handleVoteStarted)
      socket.off('vote_update', handleVoteUpdate)
      socket.off('game_restarting', handleGameRestarting)
      socket.off('game_ended', handleGameEnded)
    }
  }, [roomCode, navigate])

  function submitVote(continueGame: boolean) {
    if (myVoteSubmitted) return
    socket.emit('submit_vote', { continue_game: continueGame }, () => undefined)
    setMyVoteSubmitted(true)
  }

  // Build player order from finalScores for the table rows
  const playerIds = finalScores.map((s) => s.player_id)
  const playerNamesById: Record<string, string> = {}
  finalScores.forEach((s) => {
    playerNamesById[s.player_id] = s.player_name
  })

  const barWidth =
    voteSecondsLeft > 0 ? `${(voteSecondsLeft / 30) * 100}%` : '0%'

  const showVoteSection = voteActive || (voteResult !== null)

  return (
    <div className="postgame">
      <h1 className="postgame__header">Fim de jogo</h1>

      {/* ─── Podium ─────────────────────────────────────────────── */}
      <section>
        <div className="postgame__podium">
          {finalScores.length === 0 ? (
            <div className="postgame__podium-loading">Calculando pontuação…</div>
          ) : (
            finalScores.slice(0, 3).map((entry, idx) => (
              <div
                key={entry.player_id}
                className={`postgame__podium-card${idx === 0 ? ' postgame__podium-card--first' : ''}`}
              >
                <span className="postgame__podium-rank">{idx + 1}</span>
                <span className="postgame__podium-name">{entry.player_name}</span>
                <span className="postgame__podium-score">{entry.total} pts</span>
              </div>
            ))
          )}
        </div>
      </section>

      {/* ─── Per-turn score table ────────────────────────────────── */}
      {turnHistory.length > 0 && playerIds.length > 0 && (
        <section className="postgame__table-section">
          <h2 className="postgame__table-heading">Pontos por turno</h2>
          <table className="postgame__table">
            <thead>
              <tr>
                <th>Jogador</th>
                {turnHistory.map((t) => (
                  <th key={t.turn}>Turno {t.turn}</th>
                ))}
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {playerIds.map((pid) => {
                const playerTotal = finalScores.find((s) => s.player_id === pid)?.total ?? 0
                return (
                  <tr key={pid}>
                    <td className="postgame__table-cell">{playerNamesById[pid] ?? pid}</td>
                    {turnHistory.map((t) => (
                      <td key={t.turn} className="postgame__table-cell">
                        {t.scores[pid] ?? 0}
                      </td>
                    ))}
                    <td className="postgame__table-cell postgame__table-cell--total">
                      {playerTotal}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </section>
      )}

      {/* ─── Vote section ────────────────────────────────────────── */}
      {showVoteSection && (
        <section className="postgame__vote">
          <h2 className="postgame__vote-heading">Jogar novamente?</h2>

          {voteActive && (
            <>
              <div className="postgame__vote-timer">
                <span className="postgame__vote-timer-label">Votação encerra em</span>
                <span className="postgame__vote-timer-value">{voteSecondsLeft}s</span>
                <div className="postgame__vote-bar-track">
                  <div
                    className="postgame__vote-bar"
                    style={{
                      width: barWidth,
                      backgroundColor: voteBarColor(voteSecondsLeft),
                    }}
                  />
                </div>
              </div>

              <p className="postgame__vote-progress">
                {votesCast}/{totalPlayers} votos registrados ({yesCount} continuar)
              </p>

              {!myVoteSubmitted ? (
                <div className="postgame__vote-btn-row">
                  <button
                    type="button"
                    className="postgame__vote-btn-yes"
                    onClick={() => submitVote(true)}
                  >
                    Continuar com novos objetos
                  </button>
                  <button
                    type="button"
                    className="postgame__vote-btn-no"
                    onClick={() => submitVote(false)}
                  >
                    Encerrar partida
                  </button>
                </div>
              ) : (
                <p className="postgame__vote-status">
                  Voto registrado. Aguardando outros jogadores…
                </p>
              )}
            </>
          )}

          {/* Result banners */}
          {voteResult === 'restarting' && (
            <div className="postgame__result-banner postgame__result-banner--restarting">
              Maioria votou continuar. Nova rodada começando…
            </div>
          )}
          {voteResult === 'ended' && (
            <div className="postgame__result-banner postgame__result-banner--ended">
              <div>Partida encerrada. Obrigado por jogar!</div>
              <div className="postgame__redirect-countdown">
                Redirecionando em {redirectCountdown}…
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  )
}
