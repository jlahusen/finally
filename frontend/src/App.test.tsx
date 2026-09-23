import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { FakeEventSource, mockFetch, tick } from './test/fakes'
import type { Portfolio } from './types'

const portfolio: Portfolio = {
  cash: 8000,
  total_value: 10000,
  unrealized_pnl: 0,
  positions: [
    { ticker: 'AAPL', quantity: 10, avg_cost: 200, current_price: 200, market_value: 2000, unrealized_pnl: 0, pnl_pct: 0 },
  ],
}

describe('App', () => {
  let fetchMock: ReturnType<typeof mockFetch>

  beforeEach(() => {
    vi.stubGlobal('EventSource', FakeEventSource)
    fetchMock = mockFetch({
      'GET /api/portfolio': () => ({ body: portfolio }),
      'GET /api/watchlist': () => ({ body: [] }),
      'GET /api/portfolio/history': () => ({ body: [] }),
      'GET /api/chat': () => ({ body: [] }),
      'GET /api/health': () => ({ body: { status: 'ok', llm_available: true } }),
      'POST /api/portfolio/trade': (body) =>
        (body as { quantity: number }).quantity > 100
          ? { status: 400, body: { detail: 'insufficient cash ($30,000.00 needed, $8,000.00 available)' } }
          : { body: { trade: {}, portfolio } },
    })
  })

  it('computes the header total from live SSE prices', async () => {
    render(<App />)
    expect(await screen.findByTestId('position-row-AAPL')).toBeInTheDocument()
    expect(screen.getByTestId('header-cash')).toHaveTextContent('$8,000.00')
    expect(screen.getByTestId('header-total-value')).toHaveTextContent('$10,000.00')

    act(() => FakeEventSource.last.emit([tick('AAPL', 210)]))
    expect(screen.getByTestId('header-total-value')).toHaveTextContent('$10,100.00')
    expect(screen.getByTestId('position-row-AAPL')).toHaveTextContent('+$100.00')
  })

  it('shows the backend reason when a trade is rejected', async () => {
    render(<App />)
    await userEvent.type(screen.getByTestId('trade-ticker'), 'AAPL')
    await userEvent.type(screen.getByTestId('trade-quantity'), '150')
    await userEvent.click(screen.getByTestId('trade-buy'))
    expect(await screen.findByTestId('trade-error')).toHaveTextContent('insufficient cash')
  })

  it('re-fetches the portfolio after a successful trade', async () => {
    render(<App />)
    await userEvent.type(screen.getByTestId('trade-ticker'), 'AAPL')
    await userEvent.type(screen.getByTestId('trade-quantity'), '1')
    await userEvent.click(screen.getByTestId('trade-sell'))
    const portfolioCalls = () => fetchMock.mock.calls.filter(([url]) => url === '/api/portfolio').length
    await vi.waitFor(() => expect(portfolioCalls()).toBe(2))
    expect(screen.queryByTestId('trade-error')).not.toBeInTheDocument()
  })
})
