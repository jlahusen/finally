# FinAlly — AI Trading Workstation

## Project Specification

## 1. Vision

FinAlly (Finance Ally) is a visually stunning AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot.

The app is built entirely by Coding Agents. Agents interact through files in `/planning`. 


## 2. User Experience

### First Launch

The user runs a single Docker command (or a provided start script). A browser opens to `http://localhost:8000`. No login, no signup. They immediately see:

- A watchlist of 10 default tickers with live-updating prices in a grid
- $10,000 in virtual cash
- A dark, data-rich trading terminal aesthetic
- An AI chat panel ready to assist

### What the User Can Do

- **Watch prices stream** — prices flash green (uptick) or red (downtick) with subtle CSS animations that fade
- **View sparkline mini-charts** — price action beside each ticker in the watchlist, accumulated on the frontend from the SSE stream since page load (sparklines fill in progressively)
- **Click a ticker** to see a larger detailed chart in the main chart area
- **Buy and sell shares** — market orders only, instant fill at current price, no fees, no confirmation dialog
- **Monitor their portfolio** — a heatmap (treemap) showing positions sized by weight and colored by P&L, plus a P&L chart tracking total portfolio value over time
- **View a positions table** — ticker, quantity, average cost, current price, unrealized P&L, % change
- **Chat with the AI assistant** — ask about their portfolio, get analysis, and have the AI execute trades and manage the watchlist through natural language
- **Manage the watchlist** — add/remove tickers manually or via the AI chat

### Visual Design

- **Dark theme**: background color `#2F2F2F`, lighter grey borders, no pure black
- **Price flash animations**: brief green/red background highlight on price change, fading over ~500ms via CSS transitions
- **Connection status indicator**: a small colored dot (green = connected, yellow = reconnecting, red = disconnected) visible in the header
- **Professional, data-dense layout**: inspired by Bloomberg/trading terminals — every pixel earns its place
- **Responsive but desktop-first**: optimized for wide screens, functional on tablet

### Color Scheme
- Accent: `#D6A345`
- Primary: `#459CD6`
- Up / profit: `#46DD34`
- Down / loss: `#DD4134`
- Flash tints (price-change background, fading over ~500ms): up `rgba(70, 221, 52, 0.18)`, down `rgba(221, 65, 52, 0.18)` — translucent so they read as a highlight over `#2F2F2F` rather than a block of color

## 3. Architecture Overview

### Single Container, Single Port

```
┌─────────────────────────────────────────────────┐
│  Docker Container (port 8000)                   │
│                                                 │
│  FastAPI (Python/uv)                            │
│  ├── /api/*          REST endpoints             │
│  ├── /api/stream/*   SSE streaming              │
│  └── /*              Static file serving        │
│                      (Vite build output)        │
│                                                 │
│  SQLite database (volume-mounted)               │
│  Background task: market data polling/sim       │
└─────────────────────────────────────────────────┘
```

- **Frontend**: Vite + React with TypeScript, built to a static `dist/` bundle, served by FastAPI as static files
- **Backend**: FastAPI (Python), managed as a `uv` project
- **Database**: SQLite, single file at `db/finally.db`, volume-mounted for persistence
- **Real-time data**: Server-Sent Events (SSE) — simpler than WebSockets, one-way server→client push, works everywhere
- **AI integration**: LiteLLM → OpenRouter, with structured outputs for trade execution
- **Market data**: Environment-variable driven — simulator by default, real data via Massive API if key provided

### Why These Choices

| Decision | Rationale |
|---|---|
| SSE over WebSockets | One-way push is all we need; simpler, no bidirectional complexity, universal browser support |
| Vite static build | Single origin, no CORS issues, one port, one container, simple deployment. The app is one page with no routing, no SSR and no server components, so a static bundler is all it needs |
| SQLite over Postgres | No auth = no multi-user = no need for a database server; self-contained, zero config |
| Single Docker container | Users run one command; no docker-compose for production, no service orchestration |
| uv for Python | Fast, modern Python project management; reproducible lockfile; what users should learn |
| Market orders only | Eliminates order book, limit order logic, partial fills — dramatically simpler portfolio math |

---

## 4. Directory Structure

```
finally/
├── frontend/                 # Vite + React + TypeScript project (static build)
├── backend/                  # FastAPI uv project (Python)
│   └── db/                   # database.py (connection, lazy init, seed) + schema.sql
├── planning/                 # Project-wide documentation for agents
│   ├── PLAN.md               # This document
│   └── ...                   # Additional agent reference docs
├── scripts/
│   ├── start_mac.sh          # Launch Docker container (macOS/Linux)
│   ├── stop_mac.sh           # Stop Docker container (macOS/Linux)
│   ├── start_windows.ps1     # Launch Docker container (Windows PowerShell)
│   └── stop_windows.ps1      # Stop Docker container (Windows PowerShell)
├── test/                     # Playwright E2E tests + docker-compose.test.yml
├── db/                       # Bind mount target (SQLite file lives here at runtime)
│   └── .gitkeep              # Directory exists in repo; finally.db is gitignored
├── Dockerfile                # Multi-stage build (Node → Python)
├── docker-compose.yml        # Optional convenience wrapper
├── .env                      # Environment variables (gitignored, .env.example committed)
└── .gitignore
```

### Key Boundaries

- **`frontend/`** is a self-contained + React + TypeScript project. It knows nothing about Python. It talks to the backend via `/api/*` endpoints and `/api/stream/*` SSE endpoints. Internal structure is up to the Frontend Engineer agent.
- **`backend/`** is a self-contained uv project with its own `pyproject.toml`. It owns all server logic including database initialization, schema, seed data, API routes, SSE streaming, market data, and LLM integration. Internal structure is up to the Backend/Market Data agents.
- **`backend/db/`** contains `database.py` (connection handling, lazy initialization, seed logic) and a single `schema.sql`. The backend lazily initializes the database on first request — creating tables and seeding default data if the SQLite file doesn't exist or is empty.
- **`db/`** at the top level is the runtime bind mount point. The SQLite file (`db/finally.db`) is created here by the backend and persists across container restarts. Because it is a bind mount rather than a named volume, the file is visible in the project directory — resetting all data is `rm db/finally.db`.
- **`planning/`** contains project-wide documentation, including this plan. All agents reference files here as the shared contract.
- **`test/`** contains Playwright E2E tests and supporting infrastructure (e.g., `docker-compose.test.yml`). Unit tests live within `frontend/` and `backend/` respectively, following each framework's conventions.
- **`scripts/`** contains start/stop scripts that wrap Docker commands.

---

## 5. Environment Variables

```bash
# Required: OpenRouter API key for LLM chat functionality
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Optional: 
(Polygon.io) API key for real market data
# If not set, the built-in market simulator is used (recommended for most users)
MASSIVE_API_KEY=

# Optional: Set to "true" for deterministic mock LLM responses (testing)
LLM_MOCK=false
```

### Behavior

- If `MASSIVE_API_KEY` is set and non-empty → backend uses Massive REST API for market data
- If `MASSIVE_API_KEY` is absent or empty → backend uses the built-in market simulator
- If `LLM_MOCK=true` → backend returns deterministic mock LLM responses (for E2E tests)
- If `OPENROUTER_API_KEY` is absent and `LLM_MOCK` is false → the app starts normally and every other feature works; the chat panel shows "AI assistant unavailable — no API key configured" and the chat input is disabled. A missing key is never a startup failure.
- The backend reads `.env` from the project root (mounted into the container or read via docker `--env-file`)

---

## 6. Market Data

### Two Implementations, One Interface

Both the simulator and the Massive client implement the same abstract interface. The backend selects which to use based on the environment variable. All downstream code (SSE streaming, price cache, frontend) is agnostic to the source.

### Simulator (Default)

- Generates prices using geometric Brownian motion (GBM) with configurable drift and volatility per ticker
- Updates at ~500ms intervals
- Correlated moves across tickers (e.g., tech stocks move together)
- Occasional random "events" — sudden 2-5% moves on a ticker for drama
- Starts from realistic seed prices (e.g., AAPL ~$190, GOOGL ~$175, etc.)
- Runs as an in-process background task — no external dependencies

**Unknown tickers.** Any ticker can be added to the watchlist or traded, including ones with no built-in seed price. When the simulator encounters a ticker it doesn't know, it generates a plausible random seed price and simulates it from there. Adding a ticker never fails for being unrecognized, so no seed table needs maintaining.

**Restart continuity.** On startup, the simulator seeds each ticker from its last known price in the `last_prices` table when one exists, falling back to the built-in seed price otherwise. Without this, positions bought at a simulated $250 would reprice against a $190 seed after a restart and show a large phantom loss.

### Massive API (Optional)

See `planning/MASSIVE_API.md` for the full endpoint reference and integration design.

- REST API polling (not WebSocket) — simpler, works on all tiers
- Every poll is a **single request to the grouped snapshot endpoint** covering all tracked tickers at once. Never loop per ticker: 10 tickers every 15 seconds would be 40 calls/min, where the grouped endpoint covers all of them in a single request.
- Poll every 15 seconds. Paid tiers have no rate limit, and Starter/Developer data is 15-minute delayed, so a faster poll buys nothing on any tier
- Parses REST response into the same format as the simulator

**The free tier cannot stream prices.** Massive's Basic (free) plan is end-of-day only and excludes the snapshot endpoint entirely — a snapshot call on a free key returns `403 NOT_AUTHORIZED`. Only paid tiers can poll for live prices, and only Advanced is genuinely real-time.

**Plan detection and fallback.** Because Massive exposes no "what plan am I on?" endpoint, the backend probes at startup with one single-ticker snapshot call and branches on the result:

| Key | Probe result | Source used |
|---|---|---|
| absent | — | Simulator, built-in seed prices |
| present | snapshot works | Massive poller (real prices) |
| present | `403` — free tier | **Simulator seeded from real end-of-day closes** |
| present | `401` — bad key | Simulator, built-in seed prices, logged warning |

The free-tier path makes one call to the grouped daily-bars endpoint, which *is* included in every plan and returns the previous close for every US ticker at once. Those real closing prices become the simulator's seeds, so a free key still shows genuine market levels — they simply move under simulation rather than from the wire. Seed precedence is `last_prices` → Massive EOD close → built-in seed → generated random seed, so restart continuity still wins.

In Massive mode the cache's session open price is the real `day.open` from the snapshot rather than the first price observed after start.

### Shared Price Cache

- A single background task (simulator or Massive poller) writes to an in-memory price cache
- The cache holds, per ticker: latest price, previous price, **session open price**, and timestamp
- **Tracked tickers are the union of the watchlist and all tickers with an open position.** Removing a ticker from the watchlist only hides it from the watchlist panel — a position in it keeps its live price and the portfolio total stays correct
- The session open price is simply the first price the cache saw for that ticker after start. It is the reference for the "Chg %" column (see below); there is no concept of a trading day in the simulator
- SSE streams read from this cache and push updates to connected clients
- The cache writes each ticker's latest price to the `last_prices` table periodically (~30s) and on shutdown, so the simulator can resume from it
- This architecture supports future multi-user scenarios without changes to the data layer

### SSE Streaming

- Endpoint: `GET /api/stream/prices`
- Long-lived SSE connection; client uses native `EventSource` API
- The server ticks every ~500ms and emits **one event per tick carrying an array** of updates, rather than one event per ticker. One event instead of ten-plus, and the frontend does a single state update per tick.
- **Only tickers whose price changed since the last tick are included**, and a tick with no changes emits nothing. This matters in Massive mode, where the cache only changes every 15 seconds: pushing unconditionally would send 29 identical payloads for every real one, and the flash animation would never fire.
- A keepalive comment (`: keepalive`) goes out every ~15 seconds so an idle connection isn't dropped by a proxy.
- Event payload — an array of objects, each with:

```json
{
  "ticker": "AAPL",
  "price": 191.24,
  "previous_price": 191.02,
  "open_price": 190.10,
  "direction": "up",
  "timestamp": "2026-09-14T10:31:02.512Z"
}
```

- Both market data sources produce identical event shapes and cadence behavior, so the frontend cannot tell them apart
- Client handles reconnection automatically (EventSource has built-in retry)

---

## 7. Database

### SQLite with Lazy Initialization

The backend checks for the SQLite database on startup (or first request). If the file doesn't exist or tables are missing, it creates the schema and seeds default data. This means:

- No separate migration step
- No manual database setup
- A fresh bind mount starts with a clean, seeded database automatically

### Connections and Precision

- **WAL mode** is enabled at initialization, and each request opens its own connection. A background task writes portfolio snapshots and last prices while request handlers read and write, and the default journal mode will produce `database is locked` errors under that pattern.
- **Rounding is applied at every write**: quantities to 4 decimal places, prices and cash to 2. The buy-side cash check allows a one-cent tolerance so float drift can't reject a trade that exactly fits.

### Schema

All user-owned tables include a `user_id` column defaulting to `"default"`. This is hardcoded for now (single-user) but enables future multi-user support without schema migration. `last_prices` is the one exception — it holds market data, which belongs to no user.

**users_profile** — User state (cash balance)
- `id` TEXT PRIMARY KEY (default: `"default"`)
- `cash_balance` REAL (default: `10000.0`)
- `created_at` TEXT (ISO timestamp)

**watchlist** — Tickers the user is watching
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `added_at` TEXT (ISO timestamp)
- UNIQUE constraint on `(user_id, ticker)`

**positions** — Current holdings (one row per ticker per user). The row is **deleted when quantity reaches zero**, so the positions table and heatmap never show empty rows; the `trades` log preserves the history.
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `quantity` REAL (fractional shares supported)
- `avg_cost` REAL
- `updated_at` TEXT (ISO timestamp)
- UNIQUE constraint on `(user_id, ticker)`

**trades** — Trade history (append-only log)
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `side` TEXT (`"buy"` or `"sell"`)
- `quantity` REAL (fractional shares supported)
- `price` REAL
- `executed_at` TEXT (ISO timestamp)

**portfolio_snapshots** — Portfolio value over time (for P&L chart). A background task runs every 30 seconds and **skips the write when total value is unchanged** since the last snapshot, so an all-cash portfolio doesn't accumulate thousands of identical rows. A snapshot is also written immediately after each trade execution.
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `total_value` REAL
- `recorded_at` TEXT (ISO timestamp)

**last_prices** — Latest known price per ticker, so the simulator resumes sensibly after a restart
- `ticker` TEXT PRIMARY KEY
- `price` REAL
- `updated_at` TEXT (ISO timestamp)

**chat_messages** — Conversation history with LLM
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `role` TEXT (`"user"` or `"assistant"`)
- `content` TEXT
- `actions` TEXT (JSON — trades executed, watchlist changes made; null for user messages)
- `created_at` TEXT (ISO timestamp)

### Default Seed Data

- One user profile: `id="default"`, `cash_balance=10000.0`
- Ten watchlist entries: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX

---

## 8. API Endpoints

### Market Data
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/stream/prices` | SSE stream of live price updates |

### Portfolio
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/portfolio` | Current positions, cash balance, total value, unrealized P&L |
| POST | `/api/portfolio/trade` | Execute a trade: `{ticker, quantity, side}`. A buy auto-adds the ticker to the watchlist if absent |
| GET | `/api/portfolio/history` | Portfolio value snapshots over time (for P&L chart). Accepts `?limit=` and downsamples evenly across the range |
| GET | `/api/trades` | Trade history, most recent first. Accepts `?limit=` |

### Watchlist
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/watchlist` | Current watchlist tickers with latest prices |
| POST | `/api/watchlist` | Add a ticker: `{ticker}`. Unknown tickers are accepted and simulated from a generated seed price |
| DELETE | `/api/watchlist/{ticker}` | Remove a ticker. Allowed even while a position is open — the price cache keeps tracking it |

### Chat
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat` | Send a message, receive complete JSON response (message + executed actions) |
| GET | `/api/chat` | Recent conversation history, so the panel repopulates on page reload. Accepts `?limit=` (default 50) |

### System
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check (for Docker/deployment) |

---

## 9. LLM Integration

All LLM calls go through LiteLLM to OpenRouter using the `finally` preset — the model string is `openrouter/@preset/finally`. Structured Outputs are used to interpret the results.

There is an OPENROUTER_API_KEY in the .env file in the project root.

### How It Works

When the user sends a chat message, the backend:

1. Loads the user's current portfolio context (cash, positions with P&L, watchlist with live prices, total portfolio value)
2. Loads the last 20 messages from the `chat_messages` table (oldest trimmed — a fixed, deterministic window)
3. Constructs a prompt with a system message, portfolio context, conversation history, and the user's new message
4. Calls the LLM via LiteLLM → OpenRouter (`openrouter/@preset/finally`)
5. Parses the complete structured JSON response
6. Auto-executes any trades or watchlist changes specified in the response, recording the outcome of each
7. Stores the message and executed actions in `chat_messages`
8. Returns the complete JSON response to the frontend (no token-by-token streaming)

### Structured Output Schema

The LLM is instructed to respond with JSON matching this schema:

```json
{
  "message": "Your conversational response to the user",
  "trades": [
    {"ticker": "AAPL", "side": "buy", "quantity": 10}
  ],
  "watchlist_changes": [
    {"ticker": "PYPL", "action": "add"}
  ]
}
```

- `message` (required): The conversational text shown to the user
- `trades` (optional): Array of trades to auto-execute. Each trade goes through the same validation as manual trades (sufficient cash for buys, sufficient shares for sells)
- `watchlist_changes` (optional): Array of watchlist modifications

### Auto-Execution

Trades specified by the LLM execute automatically — no confirmation dialog. This is a deliberate design choice:
- It's a simulated environment with fake money, so the stakes are zero
- It creates an impressive, fluid demo experience
- It demonstrates agentic AI capabilities — the core theme of the course

**When an action fails**, the LLM is *not* called a second time. It has already finished speaking by the time execution happens, so a retry would double the latency and cost for no benefit. Instead, every action carries its outcome in the `actions` payload returned to the frontend, and the chat panel renders it inline as a deterministic notice beneath the assistant's message:

- `✓ Bought 10 AAPL @ $191.24`
- `✗ Buy 10 AAPL — insufficient cash ($1,912.40 needed, $840.00 available)`

This is faster, free, and directly testable. The system prompt tells the assistant to propose trades it believes will pass validation, but a failure is surfaced by the UI, not by the model.

### System Prompt Guidance

The LLM should be prompted as "FinAlly, an AI trading assistant" with instructions to:
- Analyze portfolio composition, risk concentration, and P&L
- Suggest trades with reasoning
- Execute trades when the user asks or agrees
- Manage the watchlist proactively
- Be concise and data-driven in responses
- Always respond with valid structured JSON

### LLM Mock Mode

When `LLM_MOCK=true`, the backend returns deterministic mock responses instead of calling OpenRouter. This enables:
- Fast, free, reproducible E2E tests
- Development without an API key
- CI/CD pipelines

---

## 10. Frontend Design

### Layout

The frontend is a single-page application with a terminal-inspired layout. The specific component architecture and layout system is up to the Frontend Engineer, but the UI should include these elements:

- **Watchlist panel** — grid/table of watched tickers with: ticker symbol, current price (flashing green/red on change), **Chg %** (change vs. the session open price carried in each SSE event — not a daily change, since the simulator has no trading day), and a sparkline mini-chart
- **Main chart area** — larger chart for the currently selected ticker, with at minimum price over time. Clicking a ticker in the watchlist selects it here.
- **Portfolio heatmap** — treemap visualization where each rectangle is a position, sized by portfolio weight, colored by P&L (green = profit, red = loss)
- **P&L chart** — line chart showing total portfolio value over time, using data from `portfolio_snapshots`
- **Positions table** — tabular view of all positions: ticker, quantity, avg cost, current price, unrealized P&L, % change
- **Trade bar** — simple input area: ticker field, quantity field, buy button, sell button. Market orders, instant fill.
- **AI chat panel** — docked/collapsible sidebar. Message input, scrolling conversation history (repopulated from `GET /api/chat` on load), loading indicator while waiting for LLM response. Trade executions and watchlist changes shown inline as confirmations, successes and failures alike.
- **Header** — portfolio total value (updating live), connection status indicator, cash balance

### Charts Are Session-Scoped

**Every price chart in the app — sparklines, the main chart — is built from the SSE stream since page load, and starts empty.** There is no price history endpoint and none is in scope; nothing stores OHLC bars. Charts fill in progressively as ticks arrive. The only chart with persisted history is the P&L chart, which reads `portfolio_snapshots`.

### Technical Notes

- **Vite + React + TypeScript.** No routing, no SSR — one page.
- Use `EventSource` for SSE connection to `/api/stream/prices`. Each event carries an array of changed tickers; apply them in one state update per tick.
- **Recharts for all four visuals** — sparkline, main chart, treemap heatmap, and P&L line. One charting dependency, one styling idiom. At ~10 tickers and a few hundred points, SVG rendering is not a bottleneck.
- **Portfolio total is computed on the frontend** from the position list multiplied by the latest SSE prices, so the header updates on every tick without polling. `GET /api/portfolio` is re-fetched only after a trade or a chat action changes the positions themselves.
- Price flash effect: on receiving a new price, briefly apply a CSS class with background color transition, then remove it
- All API calls go to the same origin (`/api/*`) — no CORS configuration needed
- Tailwind CSS for styling with a custom dark theme built on the Section 2 color scheme

---

## 11. Docker & Deployment

### Multi-Stage Dockerfile

```
Stage 1: Node 20 slim
  - Copy frontend/
  - npm ci && npm run build (Vite, produces dist/)

Stage 2: Python 3.12 slim
  - Install uv
  - Copy backend/
  - uv sync --frozen (install Python dependencies from lockfile)
  - Copy frontend dist/ into a static/ directory
  - Expose port 8000
  - CMD: uvicorn serving FastAPI app
```

FastAPI serves the static frontend files and all API routes on port 8000.

### Database Persistence

The SQLite database persists via a **bind mount** of the project's `db/` directory — not a named volume. The file stays visible in the project tree, so resetting all data is just deleting it.

```bash
docker run -v "$PWD/db:/app/db" -p 8000:8000 --env-file .env finally
```

The backend writes `finally.db` to `/app/db`, which is `db/finally.db` on the host.

### Start/Stop Scripts

**`scripts/start_mac.sh`** (macOS/Linux):
- Builds the Docker image if not already built (or if `--build` flag passed)
- Runs the container with the volume mount, port mapping, and `.env` file
- Prints the URL to access the app
- Optionally opens the browser

**`scripts/stop_mac.sh`** (macOS/Linux):
- Stops and removes the running container
- Does NOT touch `db/` (data persists)

**`scripts/start_windows.ps1`** / **`scripts/stop_windows.ps1`**: PowerShell equivalents for Windows. Note that the bind mount path is spelled differently — `-v "${PWD}\db:/app/db"` in PowerShell, where `$PWD` is a path object rather than a string.

All scripts should be idempotent — safe to run multiple times.

### Optional Cloud Deployment

The container is designed to deploy to Render or any container platform. A Terraform configuration for App Runner may be provided in a `deploy/` directory as a stretch goal, but is not part of the core build.

---

## 12. Testing Strategy

### Unit Tests (within `frontend/` and `backend/`)

**Backend (pytest)**:
- Market data: simulator generates valid prices, GBM math is correct, Massive API response parsing works, both implementations conform to the abstract interface, unknown tickers get a generated seed price, the simulator resumes from `last_prices` on restart, and the SSE tick emits only changed tickers
- Portfolio: trade execution logic, P&L calculations, edge cases (selling more than owned, buying with insufficient cash, selling at a loss, selling the full quantity removing the row, fractional quantities and cent-tolerance on the buy check)
- LLM: structured output parsing handles all valid schemas, graceful handling of malformed responses, trade validation within chat flow
- API routes: correct status codes, response shapes, error handling

**Frontend (React Testing Library or similar)**:
- Component rendering with mock data
- Price flash animation triggers correctly on price changes
- Connection status indicator renders all three states (connected / reconnecting / disconnected)
- Watchlist CRUD operations
- Portfolio display calculations, including the live header total derived from SSE prices
- Chat message rendering, loading state, and inline action notices for both successful and failed trades

### E2E Tests (in `test/`)

**Infrastructure**: A separate `docker-compose.test.yml` in `test/` that spins up the app container plus a Playwright container. This keeps browser dependencies out of the production image.

**Environment**: Tests run with `LLM_MOCK=true` by default for speed and determinism.

**Key Scenarios**:
- Fresh start: default watchlist appears, $10k balance shown, prices are streaming
- Add and remove a ticker from the watchlist
- Buy shares: cash decreases, position appears, portfolio updates
- Sell shares: cash increases, position updates; selling the full quantity removes the row entirely
- Portfolio visualization: heatmap renders with correct colors, P&L chart has data points
- AI chat (mocked): send a message, receive a response, trade execution appears inline
- Chat history survives a page reload

`EventSource` reconnection is browser behavior rather than our code, so it is covered by the frontend unit test for the status indicator rather than by a brittle E2E disconnect scenario.
