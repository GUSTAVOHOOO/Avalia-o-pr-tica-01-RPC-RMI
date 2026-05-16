import { useRef, useState, useEffect } from 'react'
import './ChatPanel.css'

interface ChatMessage {
  player_id: string
  player_name: string
  message: string
  timestamp: number
}

interface ChatPanelProps {
  messages: ChatMessage[]
  myPlayerId: string
  onSend: (message: string) => void
  disabled?: boolean
}

function formatTime(timestamp: number): string {
  const d = new Date(timestamp * 1000)
  const h = d.getHours().toString().padStart(2, '0')
  const m = d.getMinutes().toString().padStart(2, '0')
  return `${h}:${m}`
}

export default function ChatPanel({ messages, myPlayerId, onSend, disabled }: ChatPanelProps) {
  const [chatInput, setChatInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const userScrolledRef = useRef(false)
  const containerRef = useRef<HTMLDivElement | null>(null)

  function handleScroll() {
    const el = containerRef.current
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 32
    userScrolledRef.current = !atBottom
  }

  useEffect(() => {
    if (!userScrolledRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
      userScrolledRef.current = false
    }
  }, [messages.length])

  function handleSend() {
    const trimmed = chatInput.trim()
    if (!trimmed) return
    onSend(trimmed)
    setChatInput('')
    userScrolledRef.current = false
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <section className="chat-panel" aria-label="Chat">
      <div className="chat-panel__header">
        <h3 className="chat-panel__title">Chat</h3>
      </div>
      <div
        className="chat-panel__messages"
        ref={containerRef}
        onScroll={handleScroll}
      >
        {messages.length === 0 ? (
          <p className="chat-panel__empty">Nenhuma mensagem ainda. Seja o primeiro!</p>
        ) : (
          messages.map((msg, i) => (
            <div
              key={i}
              className={`chat-panel__message${msg.player_id === myPlayerId ? ' chat-panel__message--mine' : ''}`}
            >
              <span className="chat-panel__message-name">{msg.player_name}</span>
              <span className="chat-panel__message-text">{msg.message}</span>
              <span className="chat-panel__message-time">{formatTime(msg.timestamp)}</span>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>
      <label className="chat-panel__field">
        <span className="chat-panel__label-text">Mensagem de chat</span>
        <input
          type="text"
          maxLength={200}
          value={chatInput}
          onChange={(e) => setChatInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          aria-label="Mensagem de chat"
          placeholder="Mensagem de chat…"
          className="chat-panel__input"
        />
      </label>
      <button
        type="button"
        onClick={handleSend}
        disabled={!chatInput.trim() || disabled}
        className="chat-panel__submit"
      >
        Enviar mensagem
      </button>
    </section>
  )
}
