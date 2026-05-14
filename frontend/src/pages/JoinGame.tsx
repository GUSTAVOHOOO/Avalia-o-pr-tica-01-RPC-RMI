import { useState } from 'react'
import { useNavigate } from 'react-router'
import socket from '../socket'
import './pages.css'

export default function JoinGame() {
  const navigate = useNavigate()
  const [roomCode, setRoomCode] = useState('')
  const [playerName, setPlayerName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const canSubmit = roomCode.length === 6 && playerName.trim().length > 0 && !loading

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!canSubmit) return
    setError('')
    setLoading(true)
    socket.connect()
    socket.emit(
      'join_game',
      { player_name: playerName.trim(), room_code: roomCode },
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
    <div className="min-h-screen flex flex-col items-center justify-start px-4 pt-12 page-root">
      <div className="w-full max-w-[400px]">
        {/* Back link */}
        <button
          onClick={() => navigate('/')}
          className="text-sm mb-6 flex items-center gap-1 hover:opacity-80 transition-opacity page-back-btn"
        >
          ← Voltar
        </button>

        {/* Title */}
        <h1 className="font-semibold mb-8 page-title">
          Entrar na Partida
        </h1>

        {/* Form card */}
        <form
          onSubmit={handleSubmit}
          className="rounded-xl p-6 flex flex-col gap-5 page-form-card"
        >
          {/* Room code field */}
          <div className="flex flex-col gap-1">
            <label
              htmlFor="room-code"
              className="text-sm font-normal page-field-label"
            >
              Código da Sessão
            </label>
            <input
              id="room-code"
              type="text"
              value={roomCode}
              onChange={(e) => setRoomCode(e.target.value.toUpperCase().slice(0, 6))}
              maxLength={6}
              placeholder="XXXXXX"
              disabled={loading}
              className="rounded-lg px-3 py-2 text-base font-mono uppercase tracking-widest disabled:opacity-50 disabled:cursor-not-allowed page-input"
            />
          </div>

          {/* Nickname field */}
          <div className="flex flex-col gap-1">
            <label
              htmlFor="player-name"
              className="text-sm font-normal page-field-label"
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
              className="rounded-lg px-3 py-2 text-base disabled:opacity-50 disabled:cursor-not-allowed page-input"
            />
          </div>

          {/* Inline error */}
          {error && (
            <p className="text-sm page-error">
              {error}
            </p>
          )}

          {/* Submit button */}
          <button
            type="submit"
            disabled={!canSubmit}
            className="rounded-lg font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 page-submit-btn"
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
