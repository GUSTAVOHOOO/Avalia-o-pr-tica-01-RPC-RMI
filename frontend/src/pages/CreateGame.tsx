import { useState } from 'react'
import { useNavigate } from 'react-router'
import socket from '../socket'

export default function CreateGame() {
  const navigate = useNavigate()
  const [playerName, setPlayerName] = useState('')
  const [maxTurns, setMaxTurns] = useState(5)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const name = playerName.trim()
    if (!name) {
      setError('Informe um apelido.')
      return
    }
    setError('')
    setLoading(true)
    socket.connect()
    socket.emit(
      'create_game',
      { player_name: name, max_turns: maxTurns },
      (response: Record<string, unknown>) => {
        setLoading(false)
        if (response.error) {
          socket.disconnect()  // WR-01: don't leave socket connected on error
          setError(String(response.error))
          return
        }
        localStorage.setItem('player_id', String(response.player_id))
        localStorage.setItem('room_code', String(response.room_code))
        localStorage.setItem('is_host', 'true')
        localStorage.setItem('max_turns', String(maxTurns))
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
          Nova Partida
        </h1>

        {/* Form card */}
        <form
          onSubmit={handleSubmit}
          className="rounded-xl p-6 flex flex-col gap-5"
          style={{ backgroundColor: '#1a1d27' }}
        >
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
              pattern="[A-Za-z0-9 _-]+"
              placeholder="Seu apelido"
              disabled={loading}
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
            {error && (
              <p className="text-sm mt-1" style={{ color: '#ef4444' }}>
                {error}
              </p>
            )}
          </div>

          {/* Turn count field */}
          <div className="flex flex-col gap-1">
            <label
              htmlFor="max-turns"
              className="text-sm font-normal"
              style={{ color: '#f1f5f9' }}
            >
              Número de turnos
            </label>
            <select
              id="max-turns"
              value={maxTurns}
              onChange={(e) => setMaxTurns(Number(e.target.value))}
              disabled={loading}
              className="rounded-lg px-3 py-2 text-base disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                backgroundColor: '#0f1117',
                color: '#f1f5f9',
                border: '1px solid #2d3148',
                minHeight: '44px',
              }}
            >
              <option value={3}>3 turnos</option>
              <option value={5}>5 turnos</option>
              <option value={7}>7 turnos</option>
              <option value={10}>10 turnos</option>
            </select>
            <p className="text-xs mt-1" style={{ color: '#6b7280' }}>
              ~3 min por turno
            </p>
          </div>

          {/* Submit button */}
          <button
            type="submit"
            disabled={loading}
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
                Criando...
              </>
            ) : (
              'Criar'
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
