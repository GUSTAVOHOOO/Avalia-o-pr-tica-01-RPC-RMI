import { useState } from 'react'
import { useNavigate } from 'react-router'

export default function Landing() {
  const navigate = useNavigate()
  const [roomCode, setRoomCode] = useState('')

  function handleEnterByCode(e: React.FormEvent) {
    e.preventDefault()
    const code = roomCode.trim().toUpperCase()
    if (code.length === 6) {
      navigate(`/join/${code}`)
    }
  }

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-start px-4 pt-16"
      style={{ backgroundColor: '#0f1117' }}
    >
      {/* Header */}
      <header className="w-full max-w-[640px] flex justify-between items-center mb-16">
        <span className="text-xl font-semibold" style={{ color: '#f1f5f9' }}>
          Adivinha Aí
        </span>
        <a
          href="#regras"
          className="text-sm underline"
          style={{ color: '#6b7280' }}
        >
          Regras
        </a>
      </header>

      {/* Hero */}
      <main className="w-full max-w-[640px] flex flex-col items-center gap-6 mb-12">
        <div className="text-center">
          <h1
            className="text-3xl font-semibold mb-3"
            style={{ color: '#f1f5f9', fontSize: '28px', lineHeight: '1.1' }}
          >
            Jogo de Adivinhação Multijogador
          </h1>
          <p className="text-base" style={{ color: '#6b7280' }}>
            Cada jogador recebe uma imagem secreta. Envie dicas, adivinhe os objetos dos outros e blefe para vencer.
          </p>
        </div>

        {/* Feature cards */}
        <div className="grid grid-cols-1 gap-3 w-full mt-4">
          {[
            { title: 'Dicas em tempo real', desc: 'Envie uma palavra por turno para ajudar os outros a adivinhar.' },
            { title: 'Trocas privadas', desc: 'Negocie dicas em segredo com outros jogadores.' },
            { title: 'Espionagem', desc: 'Tente descobrir as dicas alheias — mas cuidado com as penalidades!' },
          ].map((card) => (
            <div
              key={card.title}
              className="rounded-lg p-4"
              style={{ backgroundColor: '#1a1d27' }}
            >
              <p className="font-semibold text-base mb-1" style={{ color: '#f1f5f9' }}>
                {card.title}
              </p>
              <p className="text-sm" style={{ color: '#6b7280' }}>
                {card.desc}
              </p>
            </div>
          ))}
        </div>

        {/* Primary CTA */}
        <button
          onClick={() => navigate('/create')}
          className="w-full rounded-lg font-semibold text-white transition-opacity hover:opacity-90 active:opacity-80"
          style={{
            backgroundColor: '#6366f1',
            minHeight: '44px',
            fontSize: '16px',
          }}
        >
          Criar Partida
        </button>

        {/* Secondary: enter by code */}
        <div className="w-full">
          <p className="text-sm text-center mb-3" style={{ color: '#6b7280' }}>
            — ou entre numa partida existente —
          </p>
          <form onSubmit={handleEnterByCode} className="flex gap-2">
            <input
              type="text"
              value={roomCode}
              onChange={(e) => setRoomCode(e.target.value.toUpperCase().slice(0, 6))}
              placeholder="CÓDIGO (6 letras)"
              maxLength={6}
              className="flex-1 rounded-lg px-3 py-2 font-mono text-sm uppercase"
              style={{
                backgroundColor: '#1a1d27',
                color: '#f1f5f9',
                border: '1px solid #2d3148',
                minHeight: '44px',
              }}
              aria-label="Código da partida"
            />
            <button
              type="submit"
              disabled={roomCode.length !== 6}
              className="px-5 rounded-lg font-semibold text-white disabled:opacity-50 disabled:cursor-not-allowed transition-opacity hover:opacity-90"
              style={{
                backgroundColor: '#6366f1',
                minHeight: '44px',
                fontSize: '16px',
              }}
            >
              Entrar
            </button>
          </form>
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-auto pb-8">
        <a
          href="#regras"
          className="text-sm underline"
          style={{ color: '#6b7280' }}
        >
          Ver regras completas
        </a>
      </footer>
    </div>
  )
}
