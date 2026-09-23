export type Direction = 'up' | 'down' | 'flat'

export interface PriceUpdate {
  ticker: string
  price: number
  previous_price: number
  open_price: number
  direction: Direction
  timestamp: string
}

export interface WatchlistItem {
  ticker: string
  price: number | null
  previous_price: number | null
  open_price: number | null
  direction: Direction | null
  timestamp: string | null
}

export interface Position {
  ticker: string
  quantity: number
  avg_cost: number
  current_price: number | null
  market_value: number
  unrealized_pnl: number
  pnl_pct: number
}

export interface Portfolio {
  cash: number
  total_value: number
  unrealized_pnl: number
  positions: Position[]
}

export interface Snapshot {
  total_value: number
  recorded_at: string
}

export interface ChatAction {
  type: 'trade' | 'watchlist'
  ticker: string
  ok: boolean
  text: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  actions: ChatAction[] | null
  created_at: string
}

export type ConnectionState = 'connected' | 'reconnecting' | 'disconnected'

export type PricePoint = { time: number; price: number }
