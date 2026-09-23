import { useEffect, useReducer } from 'react'
import type { ConnectionState, PricePoint, PriceUpdate } from '../types'

const MAX_POINTS = 600

export interface StreamState {
  prices: Record<string, PriceUpdate>
  history: Record<string, PricePoint[]>
  status: ConnectionState
}

type Action = { type: 'tick'; updates: PriceUpdate[] } | { type: 'status'; status: ConnectionState }

export const initialStream: StreamState = { prices: {}, history: {}, status: 'reconnecting' }

/** Applies one SSE tick (all changed tickers) or a connection status change. */
export function streamReducer(state: StreamState, action: Action): StreamState {
  if (action.type === 'status') return { ...state, status: action.status }
  const prices = { ...state.prices }
  const history = { ...state.history }
  for (const u of action.updates) {
    prices[u.ticker] = u
    const point = { time: Date.parse(u.timestamp), price: u.price }
    history[u.ticker] = [...(history[u.ticker] ?? []), point].slice(-MAX_POINTS)
  }
  return { ...state, prices, history }
}

/** Subscribes to `/api/stream/prices`; keeps latest prices and session history per ticker. */
export function usePriceStream(): StreamState {
  const [state, dispatch] = useReducer(streamReducer, initialStream)

  useEffect(() => {
    const source = new EventSource('/api/stream/prices')
    source.onopen = () => dispatch({ type: 'status', status: 'connected' })
    source.onerror = () =>
      dispatch({
        type: 'status',
        status: source.readyState === EventSource.CLOSED ? 'disconnected' : 'reconnecting',
      })
    source.onmessage = (e) => dispatch({ type: 'tick', updates: JSON.parse(e.data) })
    return () => source.close()
  }, [])

  return state
}
