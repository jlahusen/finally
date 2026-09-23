import { useState } from 'react'

interface Props {
  selected: string | null
  onTrade: (ticker: string, quantity: number, side: 'buy' | 'sell') => Promise<void>
}

/** Market-order entry: ticker, quantity, buy and sell. Keyed on the picked ticker so it resets per pick. */
export function TradeBar({ selected, onTrade }: Props) {
  const [ticker, setTicker] = useState(selected ?? '')
  const [qty, setQty] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (side: 'buy' | 'sell') => {
    const quantity = Number(qty)
    const symbol = ticker.trim().toUpperCase()
    if (!symbol || !(quantity > 0)) {
      setError('Enter a ticker and a quantity above zero')
      return
    }
    setBusy(true)
    try {
      await onTrade(symbol, quantity, side)
      setError('')
      setQty('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Trade failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2 border border-line bg-panel px-2 py-2">
      <span className="text-muted">Market order</span>
      <input
        data-testid="trade-ticker"
        value={ticker}
        onChange={(e) => setTicker(e.target.value)}
        placeholder="Ticker"
        aria-label="Ticker"
        className="w-24 border border-line bg-bg px-2 py-1 uppercase placeholder:normal-case placeholder:text-muted"
      />
      <input
        data-testid="trade-quantity"
        value={qty}
        onChange={(e) => setQty(e.target.value)}
        type="number"
        min="0"
        step="any"
        placeholder="Qty"
        aria-label="Quantity"
        className="w-24 border border-line bg-bg px-2 py-1 placeholder:text-muted"
      />
      <button
        data-testid="trade-buy"
        disabled={busy}
        onClick={() => submit('buy')}
        className="bg-up/85 px-4 py-1 font-semibold text-bg hover:bg-up disabled:opacity-50"
      >
        Buy
      </button>
      <button
        data-testid="trade-sell"
        disabled={busy}
        onClick={() => submit('sell')}
        className="bg-down/85 px-4 py-1 font-semibold text-ink hover:bg-down disabled:opacity-50"
      >
        Sell
      </button>
      {error && (
        <span data-testid="trade-error" role="alert" className="text-down">
          {error}
        </span>
      )}
    </div>
  )
}
