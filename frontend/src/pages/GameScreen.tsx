import { useEffect, useState, useRef } from 'react'
import { useParams } from 'react-router'
import socket from '../socket'
import PhaseBadge from '../components/PhaseBadge'
import CountdownDisplay from '../components/CountdownDisplay'

interface PhaseChangedPayload {
  phase: string
  remaining_seconds: number
  current_turn: number
  max_turns: number
  room_code: string
}

export default function GameScreen() {
  const { roomCode } = useParams<{ roomCode: string }>()
  const [currentPhase, setCurrentPhase] = useState<string | null>(null)
  const [remainingSeconds, setRemainingSeconds] = useState(0)
  const [currentTurn, setCurrentTurn] = useState(1)
  const [maxTurns, setMaxTurns] = useState(1)
  const [gameEnded, setGameEnded] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // playerId written in Phase 2 — available for future phases
  // const playerId = localStorage.getItem('player_id')

  useEffect(() => {
    if (!socket.connected) socket.connect()
    socket.emit('join_room', { room_code: roomCode })

    const handlePhaseChanged = (data: PhaseChangedPayload) => {
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

    const handleGameEnded = (_data: object) => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      setGameEnded(true)
    }

    socket.on('phase_changed', handlePhaseChanged)
    socket.on('game_ended', handleGameEnded)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      socket.off('phase_changed', handlePhaseChanged)
      socket.off('game_ended', handleGameEnded)
    }
  }, [roomCode])

  return (
    <div
      style={{
        backgroundColor: '#0f1117',
        minHeight: '100vh',
      }}
    >
      {/* PhaseHeader */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'row',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '8px 16px',
          backgroundColor: '#1a1d27',
          borderBottom: '1px solid #2d3148',
        }}
      >
        {/* Left: PhaseBadge */}
        <div>
          {currentPhase !== null && <PhaseBadge phase={currentPhase} />}
        </div>

        {/* Center: CountdownDisplay */}
        <div>
          {!gameEnded && currentPhase !== null && (
            <CountdownDisplay seconds={remainingSeconds} />
          )}
        </div>

        {/* Right: Turn indicator */}
        <span
          style={{
            fontSize: '14px',
            color: '#6b7280',
          }}
          aria-label={`Turno ${currentTurn} de ${maxTurns}`}
        >
          Turno {currentTurn} de {maxTurns}
        </span>
      </div>

      {/* Body area */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexGrow: 1,
          padding: '32px',
        }}
      >
        <div
          style={{
            maxWidth: '640px',
            margin: '0 auto',
          }}
        >
          {gameEnded ? (
            <p
              style={{
                fontSize: '16px',
                fontWeight: 400,
                color: '#6b7280',
              }}
            >
              Jogo encerrado. Aguardando tela de resultados...
            </p>
          ) : currentPhase === null ? (
            <p
              style={{
                fontSize: '16px',
                fontWeight: 400,
                color: '#6b7280',
              }}
            >
              Conectando...
            </p>
          ) : (
            <p
              style={{
                fontSize: '16px',
                fontWeight: 400,
                color: '#6b7280',
              }}
            >
              Aguardando ação do servidor...
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
