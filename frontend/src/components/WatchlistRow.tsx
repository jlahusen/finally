import { percent, tone } from '../format'
import { useFlash } from '../hooks/useFlash'
import type { PricePoint } from '../types'
import { Sparkline } from './Sparkline'

interface Props {
  ticker: string
  price: number | null
  openPrice: number | null
  points: PricePoint[]
  selected: boolean
  onSelect: (ticker: string) => void
  onRemove: (ticker: string) => void
}

/** One watchlist line: ticker, flashing price, Chg % vs session open, sparkline. */
export function WatchlistRow({ ticker, price, openPrice, points, selected, onSelect, onRemove }: Props) {
  const flash = useFlash(price)
  const change = price != null && openPrice ? ((price - openPrice) / openPrice) * 100 : null
  const color = change == null || change >= 0 ? 'var(--color-up)' : 'var(--color-down)'

  return (
    <tr
      data-testid={`watchlist-row-${ticker}`}
      onClick={() => onSelect(ticker)}
      className={`group cursor-pointer border-b border-line/60 hover:bg-raised ${selected ? 'bg-raised shadow-[inset_2px_0_0_var(--color-accent)]' : ''}`}
    >
      <td className="px-2 py-1 font-semibold">{ticker}</td>
      <td data-testid={`watchlist-price-${ticker}`} className={`price-cell px-2 py-1 text-right ${flash}`}>
        {price == null ? '—' : price.toFixed(2)}
      </td>
      <td data-testid={`watchlist-change-${ticker}`} className={`px-2 py-1 text-right ${tone(change ?? 0)}`}>
        {change == null ? '—' : percent(change)}
      </td>
      <td className="px-1 py-0.5">
        <Sparkline points={points} color={color} />
      </td>
      <td className="w-6 pr-1 text-right">
        <button
          data-testid={`watchlist-remove-${ticker}`}
          aria-label={`Remove ${ticker} from watchlist`}
          onClick={(e) => {
            e.stopPropagation()
            onRemove(ticker)
          }}
          className="px-1 text-muted opacity-0 group-hover:opacity-100 hover:text-down focus:opacity-100"
        >
          ×
        </button>
      </td>
    </tr>
  )
}
