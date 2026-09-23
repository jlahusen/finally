import { vi } from 'vitest'
import type { PriceUpdate } from '../types'

/** Minimal controllable stand-in for the browser EventSource. */
export class FakeEventSource {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSED = 2
  static last: FakeEventSource

  readyState = FakeEventSource.CONNECTING
  onopen: (() => void) | null = null
  onerror: (() => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  url: string

  constructor(url: string) {
    this.url = url
    FakeEventSource.last = this
  }

  open() {
    this.readyState = FakeEventSource.OPEN
    this.onopen?.()
  }

  fail(readyState: number) {
    this.readyState = readyState
    this.onerror?.()
  }

  emit(updates: PriceUpdate[]) {
    this.onmessage?.({ data: JSON.stringify(updates) })
  }

  close() {
    this.readyState = FakeEventSource.CLOSED
  }
}

export const tick = (ticker: string, price: number, open = 100): PriceUpdate => ({
  ticker,
  price,
  previous_price: price,
  open_price: open,
  direction: 'flat',
  timestamp: new Date().toISOString(),
})

type Handler = (body: unknown) => { status?: number; body?: unknown }

/** Stubs global fetch with `"METHOD /path"` keyed handlers (query string ignored). */
export function mockFetch(routes: Record<string, Handler>) {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const key = `${init?.method ?? 'GET'} ${url.split('?')[0]}`
    const handler = routes[key]
    if (!handler) throw new Error(`Unmocked request: ${key}`)
    const { status = 200, body } = handler(init?.body ? JSON.parse(String(init.body)) : undefined)
    return new Response(status === 204 ? null : JSON.stringify(body), { status })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}
