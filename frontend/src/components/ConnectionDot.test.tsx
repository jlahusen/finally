import { act, render, renderHook, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePriceStream } from '../hooks/usePriceStream'
import { FakeEventSource, tick } from '../test/fakes'
import { ConnectionDot } from './ConnectionDot'

describe('ConnectionDot', () => {
  it.each(['connected', 'reconnecting', 'disconnected'] as const)('renders the %s state', (state) => {
    render(<ConnectionDot state={state} />)
    expect(screen.getByTestId('connection-status')).toHaveAttribute('data-state', state)
  })
})

describe('usePriceStream', () => {
  beforeEach(() => vi.stubGlobal('EventSource', FakeEventSource))

  it('maps EventSource lifecycle to connection states', () => {
    const { result } = renderHook(() => usePriceStream())
    const source = FakeEventSource.last
    expect(source.url).toBe('/api/stream/prices')
    expect(result.current.status).toBe('reconnecting')

    act(() => source.open())
    expect(result.current.status).toBe('connected')

    act(() => source.fail(FakeEventSource.CONNECTING))
    expect(result.current.status).toBe('reconnecting')

    act(() => source.fail(FakeEventSource.CLOSED))
    expect(result.current.status).toBe('disconnected')
  })

  it('applies a whole tick array and accumulates history', () => {
    const { result } = renderHook(() => usePriceStream())
    act(() => FakeEventSource.last.emit([tick('AAPL', 190), tick('MSFT', 400)]))
    act(() => FakeEventSource.last.emit([tick('AAPL', 191)]))

    expect(result.current.prices.AAPL.price).toBe(191)
    expect(result.current.prices.MSFT.price).toBe(400)
    expect(result.current.history.AAPL.map((p) => p.price)).toEqual([190, 191])
  })
})
