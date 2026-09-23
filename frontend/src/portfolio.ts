import type { Position, PriceUpdate } from './types'

/** Re-values positions against the latest streamed prices. */
export function livePositions(positions: Position[], prices: Record<string, PriceUpdate>): Position[] {
  return positions.map((p) => {
    const price = prices[p.ticker]?.price ?? p.current_price ?? p.avg_cost
    const cost = p.quantity * p.avg_cost
    const marketValue = p.quantity * price
    const pnl = marketValue - cost
    return {
      ...p,
      current_price: price,
      market_value: marketValue,
      unrealized_pnl: pnl,
      pnl_pct: cost ? (pnl / cost) * 100 : 0,
    }
  })
}

/** Cash plus the market value of every position. */
export const totalValue = (cash: number, positions: Position[]) =>
  positions.reduce((sum, p) => sum + p.market_value, cash)
