import type { ChatMessage } from '../types'

/** One chat bubble plus the inline outcome of each action it triggered. */
export function ChatMessageView({ message }: { message: ChatMessage }) {
  const mine = message.role === 'user'
  return (
    <li data-testid="chat-message" data-role={message.role} className={`flex flex-col ${mine ? 'items-end' : 'items-start'}`}>
      <p
        className={`max-w-[90%] whitespace-pre-wrap px-2.5 py-1.5 leading-snug ${
          mine ? 'bg-primary/20 text-ink' : 'border-l-2 border-accent bg-raised'
        }`}
      >
        {message.content}
      </p>
      {message.actions?.map((a, i) => (
        <p
          key={i}
          data-testid="chat-action"
          data-ok={String(a.ok)}
          className={`mt-1 max-w-[90%] text-[12px] ${a.ok ? 'text-up' : 'text-down'}`}
        >
          {a.text}
        </p>
      ))}
    </li>
  )
}
