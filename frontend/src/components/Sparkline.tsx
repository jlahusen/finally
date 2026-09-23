import { Line, LineChart, YAxis } from 'recharts'
import type { PricePoint } from '../types'

interface Props {
  points: PricePoint[]
  color: string
}

/** Tiny price line built from this session's ticks. */
export function Sparkline({ points, color }: Props) {
  return (
    <LineChart width={72} height={22} data={points} margin={{ top: 2, right: 0, bottom: 2, left: 0 }}>
      <YAxis hide domain={['dataMin', 'dataMax']} />
      <Line dataKey="price" stroke={color} strokeWidth={1.25} dot={false} isAnimationActive={false} />
    </LineChart>
  )
}
