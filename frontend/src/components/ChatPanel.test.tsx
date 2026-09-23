import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { mockFetch } from '../test/fakes'
import type { ChatMessage } from '../types'
import { ChatPanel } from './ChatPanel'

const reply: ChatMessage = {
  id: 'r1',
  role: 'assistant',
  content: 'Mock reply: buy 10 AAPL, buy 999 TSLA',
  created_at: '2026-09-14T10:31:02.512Z',
  actions: [
    { type: 'trade', ticker: 'AAPL', ok: true, text: '✓ Bought 10 AAPL @ $191.24' },
    { type: 'trade', ticker: 'TSLA', ok: false, text: '✗ Buy 999 TSLA — insufficient cash ($1,912.40 needed, $840.00 available)' },
  ],
}

const setup = (llmAvailable = true, history: ChatMessage[] = []) => {
  let release = () => {}
  const pending = new Promise<void>((r) => (release = r))
  mockFetch({
    'GET /api/chat': () => ({ body: history }),
    'GET /api/health': () => ({ body: { status: 'ok', llm_available: llmAvailable } }),
    'POST /api/chat': () => ({ body: reply }),
  })
  const realFetch = globalThis.fetch
  vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
    if (init?.method === 'POST') await pending
    return realFetch(url, init)
  })
  const onActions = vi.fn()
  render(<ChatPanel onActions={onActions} />)
  return { onActions, release }
}

describe('ChatPanel', () => {
  it('repopulates history on load', async () => {
    setup(true, [{ ...reply, id: 'h1', actions: null, content: 'Earlier answer' }])
    expect(await screen.findByText('Earlier answer')).toBeInTheDocument()
  })

  it('shows loading, then the reply with success and failure notices', async () => {
    const { onActions, release } = setup()
    await userEvent.type(screen.getByTestId('chat-input'), 'buy 10 AAPL')
    await userEvent.click(screen.getByTestId('chat-send'))

    expect(screen.getByTestId('chat-loading')).toBeInTheDocument()
    expect(screen.getByTestId('chat-message')).toHaveAttribute('data-role', 'user')

    release()
    expect(await screen.findByText(reply.content)).toBeInTheDocument()
    expect(screen.queryByTestId('chat-loading')).not.toBeInTheDocument()

    const [ok, failed] = screen.getAllByTestId('chat-action')
    expect(ok).toHaveAttribute('data-ok', 'true')
    expect(ok).toHaveTextContent('✓ Bought 10 AAPL @ $191.24')
    expect(failed).toHaveAttribute('data-ok', 'false')
    expect(failed).toHaveTextContent('insufficient cash')
    expect(onActions).toHaveBeenCalledOnce()
  })

  it('sends without crypto.randomUUID (plain-HTTP, non-localhost origin)', async () => {
    const original = globalThis.crypto
    vi.stubGlobal('crypto', {})
    const { release } = setup()
    await userEvent.type(screen.getByTestId('chat-input'), 'hello')
    await userEvent.click(screen.getByTestId('chat-send'))
    release()
    expect(await screen.findByText(reply.content)).toBeInTheDocument()
    vi.stubGlobal('crypto', original)
  })

  it('disables input when no API key is configured', async () => {
    setup(false)
    expect(await screen.findByTestId('chat-unavailable')).toHaveTextContent(
      'AI assistant unavailable — no API key configured',
    )
    expect(screen.getByTestId('chat-input')).toBeDisabled()
    expect(screen.getByTestId('chat-send')).toBeDisabled()
  })
})
