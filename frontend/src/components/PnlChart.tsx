import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { money } from '../format'
import type { Snapshot } from '../types'
import { Panel } from './Panel'

const time = (iso: string) => new Date(iso).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit' })

/** Total portfolio value over time from recorded snapshots. */
export function PnlChart({ snapshots }: { snapshots: Snapshot[] }) {
  return (
    <Panel title="Portfolio value" className="h-full">
      <div data-testid="pnl-chart" data-points={snapshots.length} className="h-full w-full p-1">
        {snapshots.length === 0 ? (
          <p className="p-3 text-muted">Value history is recorded every 30 seconds and after each trade.</p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={snapshots} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="#4b4b4b" strokeDasharray="2 4" vertical={false} />
              <XAxis dataKey="recorded_at" tickFormatter={time} stroke="#9c978c" fontSize={11} minTickGap={40} />
              <YAxis
                domain={['auto', 'auto']}
                stroke="#9c978c"
                fontSize={11}
                width={80}
                orientation="right"
                tickFormatter={(v) => money(Number(v))}
              />
              <Tooltip
                labelFormatter={(l) => new Date(String(l)).toLocaleString()}
                formatter={(v) => [money(Number(v)), 'Value']}
                contentStyle={{ background: '#383838', border: '1px solid #4b4b4b' }}
              />
              <Line dataKey="total_value" stroke="#d6a345" strokeWidth={1.5} dot={snapshots.length < 3} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </Panel>
  )
}
