import { useState, type FormEvent } from 'react'
import { ApiError } from '../api'
import type { StreamState } from '../hooks/usePriceStream'
import type { WatchlistItem } from '../types'
import { Panel } from './Panel'
import { WatchlistRow } from './WatchlistRow'

interface Props {
  items: WatchlistItem[]
  stream: Pick<StreamState, 'prices' | 'history'>
  selected: string | null
  onSelect: (ticker: string) => void
  onAdd: (ticker: string) => Promise<void>
  onRemove: (ticker: string) => void
}

const addErrorText = (err: unknown, ticker: string) => {
  if (err instanceof ApiError && err.status === 409) return `${ticker} is already on the watchlist`
  if (err instanceof ApiError && err.status === 422) return 'Enter a ticker symbol like AAPL'
  return `Could not add ${ticker}`
}

/** Watched tickers with live prices, plus add/remove controls. */
export function Watchlist({ items, stream, selected, onSelect, onAdd, onRemove }: Props) {
  const [draft, setDraft] = useState('')
  const [error, setError] = useState('')

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const ticker = draft.trim().toUpperCase()
    if (!ticker) return
    try {
      await onAdd(ticker)
      setDraft('')
      setError('')
    } catch (err) {
      setError(addErrorText(err, ticker))
    }
  }

  return (
    <Panel title="Watchlist" className="h-full">
      <div className="flex h-full flex-col">
        <div className="min-h-0 flex-1 overflow-y-auto">
          <table className="w-full border-collapse">
            <thead className="sticky top-0 bg-panel text-[11px] text-muted">
              <tr>
                <th className="px-2 py-1 text-left font-normal">Ticker</th>
                <th className="px-2 py-1 text-right font-normal">Last</th>
                <th className="px-2 py-1 text-right font-normal">Chg %</th>
                <th className="px-1 py-1 text-left font-normal">Session</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const live = stream.prices[item.ticker]
                return (
                  <WatchlistRow
                    key={item.ticker}
                    ticker={item.ticker}
                    price={live?.price ?? item.price}
                    openPrice={live?.open_price ?? item.open_price}
                    points={stream.history[item.ticker] ?? []}
                    selected={item.ticker === selected}
                    onSelect={onSelect}
                    onRemove={onRemove}
                  />
                )
              })}
            </tbody>
          </table>
        </div>
        <form onSubmit={submit} className="flex shrink-0 gap-1 border-t border-line p-2">
          <input
            data-testid="watchlist-add-input"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Add ticker"
            aria-label="Ticker to add"
            className="min-w-0 flex-1 border border-line bg-bg px-2 py-1 uppercase placeholder:normal-case placeholder:text-muted"
          />
          <button
            data-testid="watchlist-add-button"
            type="submit"
            className="border border-primary px-3 py-1 text-primary hover:bg-primary hover:text-bg"
          >
            Add
          </button>
        </form>
        {error && <p className="px-2 pb-2 text-down">{error}</p>}
      </div>
    </Panel>
  )
}
