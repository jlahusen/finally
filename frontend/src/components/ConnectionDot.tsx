import type { ConnectionState } from '../types'

const COLOR: Record<ConnectionState, string> = {
  connected: 'bg-up',
  reconnecting: 'bg-accent',
  disconnected: 'bg-down',
}

const LABEL: Record<ConnectionState, string> = {
  connected: 'Live',
  reconnecting: 'Reconnecting',
  disconnected: 'Disconnected',
}

/** Colored dot showing the price stream's connection state. */
export function ConnectionDot({ state }: { state: ConnectionState }) {
  return (
    <span className="flex items-center gap-1.5 text-muted" title={`Price stream: ${LABEL[state]}`}>
      <span
        data-testid="connection-status"
        data-state={state}
        className={`inline-block h-2 w-2 rounded-full ${COLOR[state]}`}
      />
      {LABEL[state]}
    </span>
  )
}
