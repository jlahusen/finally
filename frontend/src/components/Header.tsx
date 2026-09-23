import { money } from '../format'
import type { ConnectionState } from '../types'
import { ConnectionDot } from './ConnectionDot'

interface Props {
  total: number
  cash: number
  status: ConnectionState
}

/** Top bar: brand, live portfolio total, cash and stream status. */
export function Header({ total, cash, status }: Props) {
  return (
    <header className="flex h-14 shrink-0 items-center gap-8 border-b border-line px-4">
      <h1 className="text-lg font-semibold tracking-tight">
        Fin<span className="text-accent">Ally</span>
      </h1>
      <div className="flex items-baseline gap-2">
        <span className="text-muted">Portfolio</span>
        <span data-testid="header-total-value" className="text-2xl font-semibold text-accent">
          {money(total)}
        </span>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-muted">Cash</span>
        <span data-testid="header-cash" className="text-base font-medium">
          {money(cash)}
        </span>
      </div>
      <div className="ml-auto">
        <ConnectionDot state={status} />
      </div>
    </header>
  )
}
