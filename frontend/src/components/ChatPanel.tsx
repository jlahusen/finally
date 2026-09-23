import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api } from '../api'
import { useLoader } from '../hooks/useLoader'
import type { ChatMessage } from '../types'
import { ChatMessageView } from './ChatMessageView'

let localId = 0

/** Client-side message; the counter id avoids `crypto.randomUUID`, which is missing outside secure contexts. */
const localMessage = (role: ChatMessage['role'], content: string): ChatMessage => ({
  id: `local-${++localId}`,
  role,
  content,
  actions: null,
  created_at: new Date().toISOString(),
})

const checkLlm = () => api.health().then((h) => h.llm_available)

/** Collapsible AI assistant sidebar; calls `onActions` after replies that traded or changed the watchlist. */
export function ChatPanel({ onActions }: { onActions: () => void }) {
  const [messages, , setMessages] = useLoader(api.chatHistory, [])
  const [available] = useLoader(checkLlm, true)
  const [open, setOpen] = useState(true)
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(false)
  const end = useRef<HTMLLIElement>(null)

  useEffect(() => {
    end.current?.scrollIntoView({ block: 'end' })
  }, [messages, loading])

  const send = async (e: FormEvent) => {
    e.preventDefault()
    const text = draft.trim()
    if (!text || loading) return
    setDraft('')
    setMessages((m) => [...m, localMessage('user', text)])
    setLoading(true)
    try {
      const reply = await api.sendChat(text)
      setMessages((m) => [...m, reply])
      if (reply.actions?.length) onActions()
    } catch (err) {
      const reason = err instanceof Error ? err.message : 'unknown error'
      setMessages((m) => [...m, localMessage('assistant', `The assistant could not reply: ${reason}`)])
    } finally {
      setLoading(false)
    }
  }

  if (!open) {
    return (
      <aside data-testid="chat-panel" className="flex w-9 shrink-0 flex-col border-l border-line bg-panel">
        <button onClick={() => setOpen(true)} className="h-full py-3 text-accent [writing-mode:vertical-rl]" aria-label="Open AI assistant">
          AI assistant
        </button>
      </aside>
    )
  }

  return (
    <aside data-testid="chat-panel" className="flex w-[340px] shrink-0 flex-col border-l border-line bg-panel">
      <header className="flex h-7 shrink-0 items-center justify-between border-b border-line px-2">
        <h2 className="text-[12px] font-medium text-accent">AI assistant</h2>
        <button onClick={() => setOpen(false)} className="px-1 text-muted hover:text-ink" aria-label="Collapse AI assistant">
          ⟩
        </button>
      </header>
      <ul className="flex min-h-0 flex-1 flex-col gap-2.5 overflow-y-auto p-2">
        {messages.length === 0 && (
          <li className="text-muted">Ask about your portfolio, or tell me to buy, sell or watch a ticker.</li>
        )}
        {messages.map((m) => (
          <ChatMessageView key={m.id} message={m} />
        ))}
        {loading && (
          <li data-testid="chat-loading" className="text-muted">
            <span className="animate-pulse">Thinking…</span>
          </li>
        )}
        <li ref={end} />
      </ul>
      {!available && (
        <p data-testid="chat-unavailable" className="border-t border-line px-2 py-1.5 text-accent">
          AI assistant unavailable — no API key configured
        </p>
      )}
      <form onSubmit={send} className="flex shrink-0 gap-1 border-t border-line p-2">
        <input
          data-testid="chat-input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={!available}
          placeholder="Message FinAlly"
          aria-label="Message the AI assistant"
          className="min-w-0 flex-1 border border-line bg-bg px-2 py-1 placeholder:text-muted disabled:opacity-50"
        />
        <button
          data-testid="chat-send"
          type="submit"
          disabled={!available || loading}
          className="border border-accent px-3 py-1 text-accent hover:bg-accent hover:text-bg disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </aside>
  )
}
