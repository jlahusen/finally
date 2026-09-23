import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api'
import type { WatchlistItem } from '../types'
import { Watchlist } from './Watchlist'
import { WatchlistRow } from './WatchlistRow'

const item = (ticker: string, price: number): WatchlistItem => ({
  ticker,
  price,
  previous_price: price,
  open_price: 100,
  direction: 'flat',
  timestamp: null,
})

const table = (ui: React.ReactNode) => (
  <table>
    <tbody>{ui}</tbody>
  </table>
)

describe('WatchlistRow price flash', () => {
  const row = (price: number) =>
    table(
      <WatchlistRow ticker="AAPL" price={price} openPrice={100} points={[]} selected={false} onSelect={() => {}} onRemove={() => {}} />,
    )

  it('flashes up then clears so the CSS fade can run', () => {
    vi.useFakeTimers()
    const { rerender } = render(row(100))
    const cell = screen.getByTestId('watchlist-price-AAPL')
    expect(cell).not.toHaveClass('flash-up')

    rerender(row(101))
    expect(cell).toHaveClass('flash-up')

    act(() => vi.advanceTimersByTime(500))
    expect(cell).not.toHaveClass('flash-up')
    vi.useRealTimers()
  })

  it('flashes down on a lower price', () => {
    const { rerender } = render(row(100))
    rerender(row(99))
    expect(screen.getByTestId('watchlist-price-AAPL')).toHaveClass('flash-down')
  })

  it('shows change vs the session open', () => {
    render(row(102.5))
    expect(screen.getByTestId('watchlist-change-AAPL')).toHaveTextContent('+2.50%')
  })
})

describe('Watchlist', () => {
  const setup = (onAdd = vi.fn(async () => {})) => {
    const props = { onAdd, onRemove: vi.fn(), onSelect: vi.fn() }
    render(
      <Watchlist
        items={[item('AAPL', 190), item('MSFT', 400)]}
        stream={{ prices: {}, history: {} }}
        selected="AAPL"
        {...props}
      />,
    )
    return props
  }

  it('lists tickers with their prices', () => {
    setup()
    expect(screen.getByTestId('watchlist-row-AAPL')).toBeInTheDocument()
    expect(screen.getByTestId('watchlist-price-MSFT')).toHaveTextContent('400.00')
  })

  it('adds an uppercased ticker', async () => {
    const { onAdd } = setup()
    await userEvent.type(screen.getByTestId('watchlist-add-input'), 'pypl')
    await userEvent.click(screen.getByTestId('watchlist-add-button'))
    expect(onAdd).toHaveBeenCalledWith('PYPL')
    expect(screen.getByTestId('watchlist-add-input')).toHaveValue('')
  })

  it('explains a duplicate add', async () => {
    setup(vi.fn(async () => Promise.reject(new ApiError(409, 'exists'))))
    await userEvent.type(screen.getByTestId('watchlist-add-input'), 'AAPL')
    await userEvent.click(screen.getByTestId('watchlist-add-button'))
    expect(screen.getByText('AAPL is already on the watchlist')).toBeInTheDocument()
  })

  it('removes a ticker without selecting it', async () => {
    const { onRemove, onSelect } = setup()
    await userEvent.click(screen.getByTestId('watchlist-remove-MSFT'))
    expect(onRemove).toHaveBeenCalledWith('MSFT')
    expect(onSelect).not.toHaveBeenCalled()
  })

  it('selects a ticker on row click', async () => {
    const { onSelect } = setup()
    await userEvent.click(screen.getByTestId('watchlist-row-MSFT'))
    expect(onSelect).toHaveBeenCalledWith('MSFT')
  })
})
