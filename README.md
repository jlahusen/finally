# FinAlly — AI Trading Workstation

FinAlly (Finance Ally) is a simulated trading terminal in the style of a Bloomberg workstation, with an AI copilot. It streams live prices, lets you trade a virtual $10,000 portfolio, and includes a chat assistant that can analyze your positions and place trades or edit your watchlist for you in plain English.

Everything runs in one Docker container on one port. There is no login and no setup beyond an optional API key.

## Features

- **Live price streaming.** Prices update about every 500ms over Server-Sent Events. Each price flashes green or red on a change and fades over about 500ms.
- **Watchlist.** 10 default tickers, each with a live price, change since the session open, and a sparkline. You can add or remove any ticker, including ones the simulator has never seen.
- **Main chart.** Click a ticker to see a larger price chart of the current session.
- **Trading.** Market orders fill instantly at the current price, with no fees and fractional shares supported. The app checks your cash for buys and your holdings for sells.
- **Portfolio views:**
  - a heatmap (treemap) of positions, sized by weight and colored by P&L;
  - a P&L chart of total portfolio value over time;
  - a positions table with quantity, average cost, current price, unrealized P&L and % change.
- **Live header.** Total portfolio value and cash update on every price tick. A dot shows the connection state: green is connected, yellow is reconnecting, red is disconnected.
- **AI chat assistant:**
  - it has your full portfolio in view when it answers;
  - trades and watchlist changes it proposes run automatically, and each shows a ✓ or ✗ notice inline;
  - chat history survives a page reload.
- **Market data.** A built-in simulator is the default: correlated geometric Brownian motion with occasional 2–5% jumps. Set a Massive (Polygon.io) API key to use real prices instead; on the free tier, real end-of-day closes become the simulator's starting prices.
- **Persistence.** Portfolio, trades, watchlist, chat and last prices are saved in SQLite. After a restart the simulator resumes from the last saved prices.

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite 8, Tailwind CSS 4, Recharts 3 |
| Backend | Python 3.12, FastAPI, Uvicorn, managed with `uv` |
| Real-time | Server-Sent Events (`/api/stream/prices`, native `EventSource`) |
| Database | SQLite in WAL mode, created and seeded on first use |
| AI | LiteLLM → OpenRouter (`openrouter/@preset/finally`) with structured JSON output |
| Market data | Built-in GBM simulator, or the Massive (Polygon.io) REST API |
| Testing | pytest, Vitest + React Testing Library, Playwright |
| Packaging | Multi-stage Docker build (Node 20 → Python 3.12) |

## Getting started

### Prerequisites

- Docker (Docker Desktop on macOS or Windows). On Windows, add the project folder under **Settings → Resources → File Sharing** so `db/` can be mounted.
- Optional: an [OpenRouter](https://openrouter.ai) API key for the AI assistant.

### Run

1. Create your environment file:

   ```bash
   cp .env.example .env
   ```

   Then set `OPENROUTER_API_KEY` in `.env`. Without a key, everything works except chat, which shows "AI assistant unavailable".

2. Start the app:

   ```bash
   ./scripts/start_mac.sh            # macOS / Linux
   ```
   ```powershell
   .\scripts\start_windows.ps1       # Windows PowerShell
   ```

3. Open http://localhost:8000

The image builds on the first run. Add `--build` (`-Build` on Windows) to rebuild after code changes, and `--open` (`-Open`) to open the browser. Stop the app with `./scripts/stop_mac.sh` or `.\scripts\stop_windows.ps1`. Stopping never touches your data.

### Environment variables

| Variable | Purpose |
|---|---|
| `OPENROUTER_API_KEY` | Turns on the AI chat assistant |
| `MASSIVE_API_KEY` | Optional real market data; leave empty to use the simulator |
| `LLM_MOCK` | `true` gives fixed mock chat replies (for testing; no key needed) |

### Data

The SQLite database lives at `db/finally.db` on the host, mounted into the container at `/app/db`. It survives restarts. To reset to a fresh $10,000 portfolio, stop the app and delete the file.

### Without the scripts

```bash
docker build -t finally .
docker run -d --name finally -p 8000:8000 -v "$PWD/db:/app/db" --env-file .env finally
```

Or run `docker compose up -d --build`. To use mock chat, add `-e LLM_MOCK=true` to `docker run`.

## Development

Run the backend and frontend separately, with hot reload:

```bash
cd backend && uv sync && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev    # Vite dev server; proxies /api to :8000
```

### Tests

```bash
cd backend && uv run pytest                  # backend unit tests
cd frontend && npm test                      # frontend unit tests
docker compose -f test/docker-compose.test.yml up --build \
  --abort-on-container-exit --exit-code-from playwright   # end-to-end tests
```

The end-to-end tests run against a fresh in-memory database, with `LLM_MOCK=true`.

## Project structure

```
finally/
├── frontend/                 Vite + React + TypeScript app
│   └── src/
│       ├── components/       Header, Watchlist, MainChart, TradeBar, PositionsTable,
│       │                     Heatmap, PnlChart, ChatPanel, …
│       ├── hooks/            usePriceStream (SSE), useFlash, useLoader
│       ├── api.ts            REST client
│       └── portfolio.ts      live revaluation from streamed prices
├── backend/                  FastAPI uv project
│   ├── app/                  app entry point, REST routes, background tasks
│   ├── market/               simulator, Massive client, price cache, SSE stream
│   ├── portfolio/            trade execution and valuation
│   ├── watchlist/            watchlist service and tracked tickers
│   ├── llm/                  prompt, LiteLLM client, mock, chat actions, /api/chat
│   ├── db/                   schema.sql, connection + lazy init, repository
│   └── tests/                pytest suites
├── test/                     Playwright E2E specs + docker-compose.test.yml
├── scripts/                  start/stop scripts for macOS/Linux and Windows
├── planning/                 specification (PLAN.md) and team contracts
├── db/                       runtime SQLite location (bind mount)
├── Dockerfile                multi-stage build
└── docker-compose.yml        optional convenience wrapper
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/stream/prices` | SSE stream of price updates |
| GET | `/api/portfolio` | Positions, cash, total value, P&L |
| POST | `/api/portfolio/trade` | Execute a market order `{ticker, quantity, side}` |
| GET | `/api/portfolio/history` | Portfolio value snapshots |
| GET | `/api/trades` | Trade history |
| GET / POST | `/api/watchlist` | List or add tickers |
| DELETE | `/api/watchlist/{ticker}` | Remove a ticker |
| GET / POST | `/api/chat` | Chat history, or send a message |
| GET | `/api/health` | Health check and whether chat is available |

See `planning/PLAN.md` for the full specification, and `planning/CONTRACTS.md` for the exact request and response shapes.
