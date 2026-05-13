import { useEffect, useState, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router'
import socket from '../socket'
import PlayerListItem from '../components/PlayerListItem'

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

  const playerId = localStorage.getItem('player_id') ?? ''
  const isHost = localStorage.getItem('is_host') === 'true'

  function addToast(message: string, variant: ToastVariant = 'info') {
    const id = ++toastCounter
    setToasts((prev) => [...prev, { id, message, variant }])
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3000)
  }

  const handlePlayerJoined = useCallback((data: { players: Player[] }) => {
    setPlayers(data.players)
  }, [])

  const handleGameStarted = useCallback(() => {
    setGameStarting(false)
    // Navigate to game phase placeholder (Phase 3+)
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
      if (data?.players) setPlayers(data.players)
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
    <div
      className="min-h-screen flex flex-col items-center justify-start px-4 pt-8"
      style={{ backgroundColor: '#0f1117' }}
    >
      {/* Toast container */}
      <div className="fixed top-4 right-4 flex flex-col gap-2 z-50">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className="px-4 py-2 rounded-lg text-sm text-white shadow-lg transition-opacity"
            style={{
              backgroundColor:
                toast.variant === 'success'
                  ? '#22c55e'
                  : toast.variant === 'error'
                  ? '#ef4444'
                  : '#1a1d27',
            }}
          >
            {toast.message}
          </div>
        ))}
      </div>

      <div className="w-full max-w-[480px] flex flex-col gap-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1
            className="font-semibold"
            style={{ color: '#f1f5f9', fontSize: '20px', lineHeight: '1.2' }}
          >
            Sala de Espera
          </h1>
          <span
            className="px-3 py-1 rounded-full text-xs font-mono font-semibold"
            style={{ backgroundColor: '#1a1d27', color: '#6b7280' }}
          >
            {sessionId}
          </span>
        </div>

        {/* Room code display + copy */}
        <div
          className="rounded-xl p-6 flex flex-col items-center gap-4"
          style={{ backgroundColor: '#1a1d27' }}
        >
          <p className="text-sm" style={{ color: '#6b7280' }}>
            Compartilhe o código para convidar jogadores
          </p>
          <div
            className="font-mono font-semibold tracking-widest text-center"
            style={{
              fontSize: '28px',
              lineHeight: '1.1',
              color: '#f1f5f9',
            }}
            aria-label={`Código da sala: ${sessionId}`}
          >
            {sessionId}
          </div>
          <button
            onClick={handleCopyLink}
            className="px-4 py-2 rounded-lg text-sm font-semibold transition-opacity hover:opacity-80"
            style={{
              backgroundColor: copySuccess ? '#22c55e' : '#0f1117',
              color: '#f1f5f9',
              minHeight: '36px',
              border: '1px solid #2d3148',
            }}
          >
            {copySuccess ? 'Link copiado!' : 'Copiar Link'}
          </button>
        </div>

        {/* Player count indicator */}
        <p className="text-sm text-center" style={{ color: '#6b7280' }}>
          {players.length}/6 jogadores —{' '}
          {players.length >= 2 ? 'mínimo atingido' : 'aguardando mais'}
        </p>

        {/* Player list */}
        <div className="flex flex-col gap-2">
          {players.length === 0 ? (
            <p className="text-sm text-center py-4" style={{ color: '#6b7280' }}>
              Aguardando outros jogadores...
            </p>
          ) : (
            players.map((player) => (
              <div
                key={player.player_id}
                className="opacity-0 animate-[fadeIn_200ms_ease-out_forwards]"
                style={{ animation: 'fadeIn 200ms ease-out forwards' }}
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
                aria-disabled={!canStart}
                title={players.length < 2 ? 'Aguardando pelo menos 2 jogadores' : undefined}
                className="w-full rounded-lg font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                style={{
                  backgroundColor: '#6366f1',
                  minHeight: '44px',
                  fontSize: '16px',
                }}
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
                <p className="text-xs text-center mt-1" style={{ color: '#6b7280' }}>
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
                  className="flex-1 rounded-lg font-semibold text-white transition-opacity hover:opacity-90"
                  style={{
                    backgroundColor: '#ef4444',
                    minHeight: '44px',
                    fontSize: '16px',
                  }}
                >
                  Sair mesmo assim?
                </button>
                <button
                  onClick={() => setLeaveConfirm(false)}
                  className="flex-1 rounded-lg font-semibold transition-opacity hover:opacity-80"
                  style={{
                    backgroundColor: '#1a1d27',
                    color: '#f1f5f9',
                    border: '1px solid #2d3148',
                    minHeight: '44px',
                    fontSize: '16px',
                  }}
                >
                  Cancelar
                </button>
              </>
            ) : (
              <button
                onClick={() => setLeaveConfirm(true)}
                className="flex-1 rounded-lg font-semibold transition-opacity hover:opacity-80"
                style={{
                  backgroundColor: '#1a1d27',
                  color: '#f1f5f9',
                  border: '1px solid #2d3148',
                  minHeight: '44px',
                  fontSize: '16px',
                }}
              >
                Sair do Lobby
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Inline keyframe for fade-in animation */}
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-4px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
