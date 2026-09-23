import { ResponsiveContainer, Treemap } from 'recharts'
import { percent, sign } from '../format'
import type { Position } from '../types'
import { Panel } from './Panel'

interface CellProps {
  x: number
  y: number
  width: number
  height: number
  depth: number
  name: string
  pnlPct: number
}

const FILL = { up: '#46dd34', down: '#dd4134', flat: '#6a6a6a' }

/** One treemap rectangle; color intensity grows with |P&L %| up to 5%. */
function Cell({ x, y, width, height, depth, name, pnlPct }: CellProps) {
  if (depth !== 1) return null
  const pnl = sign(pnlPct)
  const opacity = 0.25 + 0.6 * Math.min(Math.abs(pnlPct) / 5, 1)
  const roomy = width > 44 && height > 30
  return (
    <g data-testid={`heatmap-cell-${name}`} data-pnl={pnl}>
      <rect x={x} y={y} width={width} height={height} fill={FILL[pnl]} fillOpacity={opacity} stroke="#2f2f2f" strokeWidth={2} />
      {roomy && (
        <>
          <text x={x + 6} y={y + 16} fill="#e8e4da" fontSize={12} fontWeight={600}>
            {name}
          </text>
          <text x={x + 6} y={y + 30} fill="#e8e4da" fontSize={11}>
            {percent(pnlPct)}
          </text>
        </>
      )}
    </g>
  )
}

/** Positions sized by market value, colored by unrealized P&L. */
export function Heatmap({ positions }: { positions: Position[] }) {
  const data = positions.map((p) => ({ name: p.ticker, size: p.market_value, pnlPct: p.pnl_pct }))
  return (
    <Panel title="Allocation by P&L" className="h-full">
      <div data-testid="heatmap" className="h-full w-full">
        {data.length === 0 ? (
          <p className="p-3 text-muted">Your holdings will appear here, sized by weight.</p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={data}
              dataKey="size"
              isAnimationActive={false}
              content={(props) => <Cell {...(props as unknown as CellProps)} />}
            />
          </ResponsiveContainer>
        )}
      </div>
    </Panel>
  )
}
