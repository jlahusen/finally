import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { money, percent, tone } from '../format'
import type { PricePoint, PriceUpdate } from '../types'
import { Panel } from './Panel'

interface Props {
  ticker: string | null
  points: PricePoint[]
  latest?: PriceUpdate
}

const clock = (t: number) => new Date(t).toLocaleTimeString([], { hour12: false })

/** Larger session price chart for the selected ticker. */
export function MainChart({ ticker, points, latest }: Props) {
  const change = latest ? ((latest.price - latest.open_price) / latest.open_price) * 100 : 0
  const aside = latest && (
    <span className="flex gap-3">
      <span className="font-semibold">{money(latest.price)}</span>
      <span className={tone(change)}>{percent(change)} since open</span>
    </span>
  )

  return (
    <Panel title={ticker ?? 'Chart'} aside={aside} className="h-full">
      <div data-testid="main-chart" data-ticker={ticker ?? ''} className="h-full w-full p-1">
        {points.length < 2 ? (
          <p className="p-4 text-muted">
            {ticker ? `Collecting ${ticker} prices since page load…` : 'Select a ticker from the watchlist.'}
          </p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="main-fill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#459cd6" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#459cd6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#4b4b4b" strokeDasharray="2 4" vertical={false} />
              <XAxis dataKey="time" tickFormatter={clock} stroke="#9c978c" fontSize={11} minTickGap={60} />
              <YAxis domain={['auto', 'auto']} stroke="#9c978c" fontSize={11} width={56} orientation="right" />
              <Tooltip
                labelFormatter={(t) => clock(Number(t))}
                formatter={(v) => [money(Number(v)), ticker]}
                contentStyle={{ background: '#383838', border: '1px solid #4b4b4b' }}
              />
              <Area dataKey="price" stroke="#459cd6" strokeWidth={1.5} fill="url(#main-fill)" isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </Panel>
  )
}
