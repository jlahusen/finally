import type { ChatMessage, Portfolio, Snapshot, WatchlistItem } from './types'

/** Error carrying the HTTP status and the backend's `detail` message. */
export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const detail = typeof body.detail === 'string' ? body.detail : res.statusText
    throw new ApiError(res.status, detail)
  }
  return res.status === 204 ? (undefined as T) : res.json()
}

const post = <T>(path: string, body: unknown) =>
  request<T>(path, { method: 'POST', body: JSON.stringify(body) })

export const api = {
  health: () => request<{ status: string; llm_available: boolean }>('/api/health'),
  portfolio: () => request<Portfolio>('/api/portfolio'),
  history: () => request<Snapshot[]>('/api/portfolio/history?limit=200'),
  trade: (ticker: string, quantity: number, side: 'buy' | 'sell') =>
    post<{ portfolio: Portfolio }>('/api/portfolio/trade', { ticker, quantity, side }),
  watchlist: () => request<WatchlistItem[]>('/api/watchlist'),
  addTicker: (ticker: string) => post<WatchlistItem>('/api/watchlist', { ticker }),
  removeTicker: (ticker: string) =>
    request<void>(`/api/watchlist/${encodeURIComponent(ticker)}`, { method: 'DELETE' }),
  chatHistory: () => request<ChatMessage[]>('/api/chat?limit=50'),
  sendChat: (message: string) => post<ChatMessage>('/api/chat', { message }),
}
