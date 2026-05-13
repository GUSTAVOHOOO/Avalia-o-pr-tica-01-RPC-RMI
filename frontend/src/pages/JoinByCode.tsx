import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import socket from '../socket'

export default function JoinByCode() {
  const navigate = useNavigate()
  const { code = '' } = useParams<{ code: string }>()
  const [playerName, setPlayerName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const canSubmit = playerName.trim().length > 0 && !loading

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!canSubmit) return
    setError('')
    setLoading(true)
    socket.connect()
    socket.emit(
      'join_game',
      { player_name: playerName.trim(), room_code: code.toUpperCase() },
      (response: Record<string, unknown>) => {
        setLoading(false)
        if (response.error) {
          socket.disconnect()  // WR-01: don't leave socket connected on error
          const err = String(response.error)
          if (err === 'jogo em andamento') {
            setError('O jogo já começou.')
          } else if (err === 'sala nao encontrada') {
            setError('Sessão não encontrada ou expirada.')
          } else if (err === 'sala cheia') {
            setError('Sala cheia — tente criar uma nova partida.')
          } else {
            setError(err)
          }
          return
        }
        localStorage.setItem('player_id', String(response.player_id))
        localStorage.setItem('room_code', String(response.room_code))
        localStorage.setItem('is_host', 'false')
        localStorage.setItem('max_turns', String(response.max_turns ?? 5))
        navigate(`/lobby/${response.room_code}`)
      },
    )
  }

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-start px-4 pt-12"
      style={{ backgroundColor: '#0f1117' }}
    >
      <div className="w-full max-w-[400px]">
        {/* Back link */}
        <button
          onClick={() => navigate('/')}
          className="text-sm mb-6 flex items-center gap-1 hover:opacity-80 transition-opacity"
          style={{ color: '#6b7280' }}
        >
          ← Voltar
        </button>

        {/* Title */}
        <h1
          className="font-semibold mb-8"
          style={{ color: '#f1f5f9', fontSize: '20px', lineHeight: '1.2' }}
        >
          Entrar na Partida
        </h1>

        {/* Form card */}
        <form
          onSubmit={handleSubmit}
          className="rounded-xl p-6 flex flex-col gap-5"
          style={{ backgroundColor: '#1a1d27' }}
        >
          {/* Room code pre-filled + disabled */}
          <div className="flex flex-col gap-1">
            <label
              htmlFor="room-code"
              className="text-sm font-normal"
              style={{ color: '#f1f5f9' }}
            >
              Código da Sessão
            </label>
            <input
              id="room-code"
              type="text"
              value={code.toUpperCase()}
              disabled
              readOnly
              className="rounded-lg px-3 py-2 text-base font-mono uppercase tracking-widest opacity-60 cursor-not-allowed"
              style={{
                backgroundColor: '#0f1117',
                color: '#f1f5f9',
                border: '1px solid #2d3148',
                minHeight: '44px',
              }}
              aria-label={`Código da sala: ${code.toUpperCase()}`}
            />
          </div>

          {/* Nickname field */}
          <div className="flex flex-col gap-1">
            <label
              htmlFor="player-name"
              className="text-sm font-normal"
              style={{ color: '#f1f5f9' }}
            >
              Apelido
            </label>
            <input
              id="player-name"
              type="text"
              value={playerName}
              onChange={(e) => setPlayerName(e.target.value)}
              maxLength={20}
              placeholder="Seu apelido"
              disabled={loading}
              autoFocus
              className="rounded-lg px-3 py-2 text-base disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                backgroundColor: '#0f1117',
                color: '#f1f5f9',
                border: '1px solid #2d3148',
                minHeight: '44px',
              }}
              onFocus={(e) => (e.currentTarget.style.borderColor = '#6366f1')}
              onBlur={(e) => (e.currentTarget.style.borderColor = '#2d3148')}
            />
          </div>

          {/* Inline error */}
          {error && (
            <p className="text-sm" style={{ color: '#ef4444' }}>
              {error}
            </p>
          )}

          {/* Submit button */}
          <button
            type="submit"
            disabled={!canSubmit}
            className="rounded-lg font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            style={{
              backgroundColor: '#6366f1',
              minHeight: '44px',
              fontSize: '16px',
            }}
          >
            {loading ? (
              <>
                <span
                  className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"
                  aria-hidden="true"
                />
                Entrando...
              </>
            ) : (
              'Entrar'
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
