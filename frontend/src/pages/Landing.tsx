import { useState } from 'react'
import { useNavigate } from 'react-router'
import './pages.css'

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
    <div className="landing min-h-screen flex flex-col items-center justify-start px-4 pt-16">
      {/* Header */}
      <header className="landing__header w-full max-w-[640px] flex justify-between items-center mb-16">
        <span className="landing__brand text-xl font-semibold">
          Adivinha Aí
        </span>
        <a
          href="#regras"
          className="landing__link text-sm underline"
        >
          Regras
        </a>
      </header>

      {/* Hero */}
      <main className="landing__main w-full max-w-[640px] flex flex-col items-center gap-6 mb-12">
        <div className="text-center">
          <h1 className="landing__title text-3xl font-semibold mb-3">
            Jogo de Adivinhação Multijogador
          </h1>
          <p className="landing__subtitle text-base">
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
            <div key={card.title} className="landing__feature-card rounded-lg p-4 transition-opacity hover:opacity-90 cursor-default">
              <p className="landing__feature-title font-semibold text-base mb-1">
                {card.title}
              </p>
              <p className="landing__feature-desc text-sm">
                {card.desc}
              </p>
            </div>
          ))}
        </div>

        {/* Primary CTA */}
        <button
          onClick={() => navigate('/create')}
          className="landing__primary-btn w-full rounded-lg font-semibold text-white transition-opacity hover:opacity-90 active:opacity-80 active:scale-[0.99]"
        >
          Criar Partida
        </button>

        {/* Secondary: enter by code */}
        <div className="w-full">
          <p className="landing__divider text-sm text-center mb-3">
            — ou entre numa partida existente —
          </p>
          <form onSubmit={handleEnterByCode} className="landing__code-form flex gap-2">
            <input
              type="text"
              value={roomCode}
              onChange={(e) => setRoomCode(e.target.value.toUpperCase().slice(0, 6))}
              placeholder="CÓDIGO (6 letras)"
              maxLength={6}
              className="landing__code-input flex-1 rounded-lg px-3 py-2 font-mono text-sm uppercase"
              aria-label="Código da partida"
            />
            <button
              type="submit"
              disabled={roomCode.length !== 6}
              className="landing__code-submit px-5 rounded-lg font-semibold text-white disabled:opacity-50 disabled:cursor-not-allowed transition-opacity hover:opacity-90"
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
          className="landing__link text-sm underline"
        >
          Ver regras completas
        </a>
      </footer>
    </div>
  )
}
