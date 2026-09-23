import { money, percent, quantity, signedMoney, tone } from '../format'
import type { Position } from '../types'
import { Panel } from './Panel'

const HEADINGS = ['Ticker', 'Qty', 'Avg cost', 'Last', 'Unrealized P&L', '% chg']

/** Holdings valued at live prices. */
export function PositionsTable({ positions }: { positions: Position[] }) {
  return (
    <Panel title="Positions" className="h-full">
      <div className="h-full overflow-y-auto">
        <table data-testid="positions-table" className="w-full border-collapse">
          <thead className="sticky top-0 bg-panel text-[11px] text-muted">
            <tr>
              {HEADINGS.map((h, i) => (
                <th key={h} className={`px-2 py-1 font-normal ${i ? 'text-right' : 'text-left'}`}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {positions.map((p) => (
              <tr key={p.ticker} data-testid={`position-row-${p.ticker}`} className="border-b border-line/60">
                <td className="px-2 py-1 font-semibold">{p.ticker}</td>
                <td className="px-2 py-1 text-right">{quantity(p.quantity)}</td>
                <td className="px-2 py-1 text-right">{money(p.avg_cost)}</td>
                <td className="px-2 py-1 text-right">{money(p.current_price ?? p.avg_cost)}</td>
                <td className={`px-2 py-1 text-right ${tone(p.unrealized_pnl)}`}>{signedMoney(p.unrealized_pnl)}</td>
                <td className={`px-2 py-1 text-right ${tone(p.pnl_pct)}`}>{percent(p.pnl_pct)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {positions.length === 0 && <p className="p-3 text-muted">No positions yet. Place a buy order to open one.</p>}
      </div>
    </Panel>
  )
}
