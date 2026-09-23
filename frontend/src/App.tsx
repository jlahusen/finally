import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import { ChatPanel } from './components/ChatPanel'
import { Header } from './components/Header'
import { Heatmap } from './components/Heatmap'
import { MainChart } from './components/MainChart'
import { PnlChart } from './components/PnlChart'
import { PositionsTable } from './components/PositionsTable'
import { TradeBar } from './components/TradeBar'
import { Watchlist } from './components/Watchlist'
import { useLoader } from './hooks/useLoader'
import { usePriceStream } from './hooks/usePriceStream'
import { livePositions, totalValue } from './portfolio'
import type { Portfolio } from './types'

const EMPTY_PORTFOLIO: Portfolio = { cash: 0, total_value: 0, unrealized_pnl: 0, positions: [] }
const HISTORY_POLL_MS = 30_000

export default function App() {
  const stream = usePriceStream()
  const [portfolio, reloadPortfolio] = useLoader(api.portfolio, EMPTY_PORTFOLIO)
  const [watchlist, reloadWatchlist] = useLoader(api.watchlist, [])
  const [snapshots, reloadHistory] = useLoader(api.history, [])
  const [picked, setPicked] = useState<string | null>(null)
  const selected = picked ?? watchlist[0]?.ticker ?? null

  useEffect(() => {
    const timer = setInterval(() => reloadHistory().catch(() => {}), HISTORY_POLL_MS)
    return () => clearInterval(timer)
  }, [reloadHistory])

  const refreshAll = useCallback(() => {
    Promise.all([reloadPortfolio(), reloadWatchlist(), reloadHistory()]).catch(() => {})
  }, [reloadPortfolio, reloadWatchlist, reloadHistory])

  const trade = async (ticker: string, quantity: number, side: 'buy' | 'sell') => {
    await api.trade(ticker, quantity, side)
    refreshAll()
  }

  const addTicker = async (ticker: string) => {
    await api.addTicker(ticker)
    await reloadWatchlist()
  }

  const removeTicker = (ticker: string) => {
    api.removeTicker(ticker).finally(() => reloadWatchlist())
  }

  const positions = livePositions(portfolio.positions, stream.prices)

  return (
    <div className="flex h-full min-h-[640px] flex-col">
      <Header total={totalValue(portfolio.cash, positions)} cash={portfolio.cash} status={stream.status} />
      <div className="flex min-h-0 flex-1">
        <main className="grid min-h-0 min-w-0 flex-1 grid-cols-[minmax(300px,360px)_minmax(0,1fr)] gap-1.5 p-1.5">
          <Watchlist
            items={watchlist}
            stream={stream}
            selected={selected}
            onSelect={setPicked}
            onAdd={addTicker}
            onRemove={removeTicker}
          />
          <div className="grid min-h-0 grid-rows-[minmax(0,1.4fr)_auto_minmax(0,1fr)_minmax(0,0.9fr)] gap-1.5">
            <MainChart
              ticker={selected}
              points={selected ? (stream.history[selected] ?? []) : []}
              latest={selected ? stream.prices[selected] : undefined}
            />
            <TradeBar key={picked} selected={picked} onTrade={trade} />
            <div className="grid min-h-0 grid-cols-2 gap-1.5">
              <Heatmap positions={positions} />
              <PnlChart snapshots={snapshots} />
            </div>
            <PositionsTable positions={positions} />
          </div>
        </main>
        <ChatPanel onActions={refreshAll} />
      </div>
    </div>
  )
}
