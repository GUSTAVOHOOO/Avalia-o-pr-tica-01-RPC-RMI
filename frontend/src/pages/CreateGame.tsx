import { useState } from 'react'
import { useNavigate } from 'react-router'
import socket from '../socket'
import './pages.css'

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
      className="min-h-screen flex flex-col items-center justify-start px-4 pt-12 page-root"
    >
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
          Nova Partida
        </h1>

        {/* Form card */}
        <form
          onSubmit={handleSubmit}
          className="rounded-xl p-6 flex flex-col gap-5 page-form-card"
        >
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
              pattern="[A-Za-z0-9 _-]+"
              placeholder="Seu apelido"
              disabled={loading}
              className="rounded-lg px-3 py-2 text-base disabled:opacity-50 disabled:cursor-not-allowed page-input"
            />
            {error && (
              <p className="text-sm mt-1 page-error">
                {error}
              </p>
            )}
          </div>

          {/* Turn count field */}
          <div className="flex flex-col gap-1">
            <label
              htmlFor="max-turns"
              className="text-sm font-normal page-field-label"
            >
              Número de turnos
            </label>
            <select
              id="max-turns"
              value={maxTurns}
              onChange={(e) => setMaxTurns(Number(e.target.value))}
              disabled={loading}
              className="rounded-lg px-3 py-2 text-base disabled:opacity-50 disabled:cursor-not-allowed page-input"
            >
              <option value={3}>3 turnos</option>
              <option value={5}>5 turnos</option>
              <option value={7}>7 turnos</option>
              <option value={10}>10 turnos</option>
            </select>
            <p className="text-xs mt-1 page-hint">
              ~3 min por turno
            </p>
          </div>

          {/* Submit button */}
          <button
            type="submit"
            disabled={loading}
            className="rounded-lg font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 page-submit-btn"
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
