import { useEffect, useRef, useState, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router'
import socket from '../socket'
import PlayerListItem from '../components/PlayerListItem'
import './Lobby.css'

interface Player {
  player_id: string
  player_name: string
  is_host: boolean
}

type ToastVariant = 'success' | 'error' | 'info'

interface Toast {
  id: number
  message: string
  variant: ToastVariant
}

let toastCounter = 0

export default function Lobby() {
  const navigate = useNavigate()
  const { sessionId } = useParams<{ sessionId: string }>()

  const [players, setPlayers] = useState<Player[]>([])
  const [gameStarting, setGameStarting] = useState(false)
  const [copySuccess, setCopySuccess] = useState(false)
  const [leaveConfirm, setLeaveConfirm] = useState(false)
  const [toasts, setToasts] = useState<Toast[]>([])
  // Ref keeps the latest players list accessible inside stable callbacks (avoids stale closure)
  const playersRef = useRef<Player[]>([])

  const playerId = localStorage.getItem('player_id') ?? ''
  const isHost = localStorage.getItem('is_host') === 'true'

  function addToast(message: string, variant: ToastVariant = 'info') {
    const id = ++toastCounter
    setToasts((prev) => [...prev, { id, message, variant }])
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3000)
  }

  const handlePlayerJoined = useCallback((data: { players: Player[] }) => {
    setPlayers(data.players)
    playersRef.current = data.players
    localStorage.setItem('players', JSON.stringify(data.players))
  }, [])

  const handleGameStarted = useCallback((data?: { players?: Player[] }) => {
    setGameStarting(false)
    // Use server-provided list; fall back to the most recent local state (playersRef)
    // so localStorage is always written with the full roster before GameScreen mounts
    const finalPlayers = data?.players ?? playersRef.current
    if (finalPlayers.length > 0) {
      localStorage.setItem('players', JSON.stringify(finalPlayers))
    }
    navigate(`/game/${sessionId}`)
  }, [navigate, sessionId])

  const handleHostChanged = useCallback((data: { new_host_id: string; players: Player[] }) => {
    // CR-02: server sends new_host_id, not new_host_name; compare by ID directly
    if (data.players) setPlayers(data.players)
    const newIsHost = data.new_host_id === playerId
    if (newIsHost) {
      localStorage.setItem('is_host', 'true')
      addToast('Você é o novo host!', 'info')
    } else {
      const newHostPlayer = data.players?.find((p) => p.player_id === data.new_host_id)
      addToast(`Novo host: ${newHostPlayer?.player_name ?? 'desconhecido'}`, 'info')
    }
  }, [playerId])

  useEffect(() => {
    if (!socket.connected) {
      socket.connect()
    }

    // CR-01: fetch current player list on mount so the host (and any player
    // who joins before the Lobby renders) sees the correct list immediately
    socket.emit('get_players', { room_code: sessionId }, (data: { players?: Player[]; error?: string }) => {
      if (data?.players) {
        setPlayers(data.players)
        playersRef.current = data.players
        localStorage.setItem('players', JSON.stringify(data.players))
      }
    })

    socket.on('player_joined', handlePlayerJoined)
    socket.on('game_started', handleGameStarted)
    socket.on('host_changed', handleHostChanged)

    return () => {
      socket.off('player_joined', handlePlayerJoined)
      socket.off('game_started', handleGameStarted)
      socket.off('host_changed', handleHostChanged)
    }
  }, [handlePlayerJoined, handleGameStarted, handleHostChanged, sessionId])

  function handleCopyLink() {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(window.location.href).then(() => {
        setCopySuccess(true)
        setTimeout(() => setCopySuccess(false), 2000)
      })
    } else {
      // Fallback: cannot copy automatically
      addToast('Selecione e copie o link manualmente.', 'info')
    }
  }

  function handleStartGame() {
    if (!isHost || players.length < 2) return
    setGameStarting(true)
    // WR-02: ack callback resets spinner on failure; max_turns removed (CR-04)
    socket.emit('start_game', { player_id: playerId }, (resp: { success: boolean; error?: string }) => {
      if (!resp.success) {
        setGameStarting(false)
        addToast(resp.error ?? 'Não foi possível iniciar o jogo.', 'error')
      }
    })
  }

  function handleLeaveConfirm() {
    socket.disconnect()
    navigate('/')
  }

  const canStart = isHost && players.length >= 2 && !gameStarting

  return (
    <div className="lobby-root min-h-screen flex flex-col items-center justify-start px-4 pt-8">
      {/* Toast container */}
      <div className="fixed top-4 right-4 flex flex-col gap-2 z-50">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`px-4 py-2 rounded-lg text-sm text-white shadow-lg transition-opacity lobby-toast--${toast.variant}`}
          >
            {toast.message}
          </div>
        ))}
      </div>

      <div className="w-full max-w-[480px] flex flex-col gap-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="lobby-title font-semibold">
            Sala de Espera
          </h1>
          <span className="lobby-session-badge px-3 py-1 rounded-full text-xs font-mono font-semibold">
            {sessionId}
          </span>
        </div>

        {/* Room code display + copy */}
        <div className="lobby-code-card rounded-xl p-6 flex flex-col items-center gap-4">
          <p className="lobby-code-hint text-sm">
            Compartilhe o código para convidar jogadores
          </p>
          <div
            className="lobby-code-display font-mono font-semibold tracking-widest text-center"
            aria-label={`Código da sala: ${sessionId}`}
          >
            {sessionId}
          </div>
          <button
            onClick={handleCopyLink}
            className={`lobby-copy-btn px-4 py-2 rounded-lg text-sm font-semibold transition-opacity hover:opacity-80 ${copySuccess ? 'lobby-copy-btn--copied' : 'lobby-copy-btn--default'}`}
          >
            {copySuccess ? 'Link copiado!' : 'Copiar Link'}
          </button>
        </div>

        {/* Player count indicator */}
        <p className="lobby-player-count text-sm text-center">
          {players.length}/6 jogadores —{' '}
          {players.length >= 2 ? 'mínimo atingido' : 'aguardando mais'}
        </p>

        {/* Player list */}
        <div className="flex flex-col gap-2">
          {players.length === 0 ? (
            <p className="lobby-waiting-text text-sm text-center py-4">
              Aguardando outros jogadores...
            </p>
          ) : (
            players.map((player) => (
              <div
                key={player.player_id}
                className="lobby-player-item opacity-0 animate-[fadeIn_200ms_ease-out_forwards]"
              >
                <PlayerListItem player={player} currentPlayerId={playerId} />
              </div>
            ))
          )}
        </div>

        {/* Footer actions */}
        <div className="flex flex-col gap-3 mt-4 pb-8">
          {/* Start game (host only) */}
          {isHost && (
            <div className="relative group">
              <button
                onClick={handleStartGame}
                disabled={!canStart}
                aria-disabled={!canStart ? 'true' : 'false'}
                title={players.length < 2 ? 'Aguardando pelo menos 2 jogadores' : undefined}
                className="lobby-start-btn w-full rounded-lg font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {gameStarting ? (
                  <>
                    <span
                      className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"
                      aria-hidden="true"
                    />
                    Distribuindo imagens...
                  </>
                ) : (
                  'Iniciar Jogo'
                )}
              </button>
              {players.length < 2 && !gameStarting && (
                <p className="lobby-helper-text text-xs text-center mt-1">
                  Aguardando pelo menos 2 jogadores
                </p>
              )}
            </div>
          )}

          {/* Leave lobby */}
          <div className="flex gap-2">
            {leaveConfirm ? (
              <>
                <button
                  onClick={handleLeaveConfirm}
                  className="lobby-btn-danger flex-1 rounded-lg font-semibold text-white transition-opacity hover:opacity-90"
                >
                  Sair mesmo assim?
                </button>
                <button
                  onClick={() => setLeaveConfirm(false)}
                  className="lobby-btn-secondary flex-1 rounded-lg font-semibold transition-opacity hover:opacity-80"
                >
                  Cancelar
                </button>
              </>
            ) : (
              <button
                onClick={() => setLeaveConfirm(true)}
                className="lobby-btn-secondary flex-1 rounded-lg font-semibold transition-opacity hover:opacity-80"
              >
                Sair do Lobby
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
