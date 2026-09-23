# FinAlly — Team Contracts

Shared interface contract for the agent team. `PLAN.md` is the spec; this file pins down the seams between agents so they can work in parallel. If you need to change a contract, message the owning agent and the lead first, then update this file.

## Team & Ownership

| Agent | Owns |
|---|---|
| `db-engineer` | `backend/db/` (database.py, schema.sql, repository.py), `backend/tests/db/` |
| `backend-engineer` | `backend/app/` (FastAPI app, routes, lifespan, static serving), `backend/market/`, `backend/portfolio/`, `backend/watchlist/`, their tests |
| `llm-engineer` | `backend/llm/` (LiteLLM client, prompt, structured output, mock, chat service + `/api/chat` router), `backend/tests/llm/` |
| `frontend-engineer` | `frontend/` |
| `devops-engineer` | `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `scripts/`, `.env.example`, `README.md` run instructions |
| `integration-tester` | `test/` (Playwright + `docker-compose.test.yml`) |

Rules: edit only files you own. Do **not** `git commit` — the lead commits. Add Python deps with `uv add` from `backend/` (already present: fastapi, uvicorn[standard], litellm, python-dotenv, httpx, numpy; dev: pytest, pytest-asyncio).

## Backend layout (`backend/`, run everything from here)

Flat top-level packages; `pythonpath = ["."]` is set for pytest. Run: `uv run uvicorn app.main:app --port 8000`. Tests: `uv run pytest`.

```
backend/
  app/main.py          FastAPI app, lifespan (start market task, snapshot task), include routers, static mount
  db/database.py       get_connection(), init_db(), DB path
  db/schema.sql
  db/repository.py     all SQL
  market/              interface, simulator, massive client, price cache, SSE
  portfolio/service.py trade execution + valuation
  watchlist/service.py add/remove/list
  llm/                 chat
  static/              (Docker only) Vite dist copied here; served at /
```

### `db` (db-engineer)
- DB path: env `FINALLY_DB_PATH`, default `<project root>/db/finally.db` (i.e. `Path(__file__).resolve().parents[2] / "db" / "finally.db"`). In Docker the backend lives at `/app/backend`, so the default resolves to `/app/db/finally.db`.
- `get_connection() -> sqlite3.Connection` — new connection per call, `row_factory = sqlite3.Row`, lazily runs `init_db()` once per process (creates schema + seed if missing), WAL on.
- `repository.py` — plain functions taking `conn` first, `user_id="default"` last. Rounding on every write (qty 4dp, price/cash 2dp). Tickers stored uppercase.
  - `get_cash(conn) -> float`, `set_cash(conn, cash)`
  - `list_watchlist(conn) -> list[str]` (in added order), `add_watchlist(conn, ticker) -> bool` (False if already present), `remove_watchlist(conn, ticker) -> bool` (False if absent)
  - `list_positions(conn) -> list[dict]` keys `ticker, quantity, avg_cost`; `get_position(conn, ticker) -> dict | None`
  - `save_position(conn, ticker, quantity, avg_cost)` — deletes the row when rounded quantity is 0
  - `insert_trade(conn, ticker, side, quantity, price) -> dict` (`id, ticker, side, quantity, price, executed_at`); `list_trades(conn, limit=50) -> list[dict]` newest first
  - `insert_snapshot(conn, total_value)`, `last_snapshot_value(conn) -> float | None`, `list_snapshots(conn, limit=200) -> list[dict]` (`total_value, recorded_at`, oldest first, evenly downsampled to ≤ limit, always keeping the latest)
  - `load_last_prices(conn) -> dict[str, float]`, `save_last_prices(conn, prices: dict[str, float])`
  - `insert_chat_message(conn, role, content, actions: list | None) -> dict`, `list_chat_messages(conn, limit=50) -> list[dict]` (`id, role, content, actions` (parsed list or None), `created_at`; the *latest* `limit`, returned oldest first)
- Timestamps: ISO 8601 UTC with `Z`, e.g. `2026-09-14T10:31:02.512Z`.
- Callers own transactions: use `with conn:` around multi-statement writes (a trade = cash + position + trade + snapshot in one transaction).

### `market` (backend-engineer)
- Module singleton `market.cache.price_cache` with `get(ticker) -> PriceUpdate | None`, `prices() -> dict[str, float]`, `track(ticker)`, `untrack(ticker)` (the market source picks tracked tickers up on its next tick).
- `PriceUpdate` fields = the SSE payload: `ticker, price, previous_price, open_price, direction ("up"|"down"|"flat"), timestamp`.
- Tracked = watchlist ∪ open positions. `track()` on an unknown ticker must make a price available within one tick (simulator generates a seed).

### `portfolio` / `watchlist` (backend-engineer) — used by routes AND by `llm`
- `portfolio.service.execute_trade(ticker, side, quantity) -> dict` — opens its own connection, validates, executes, writes snapshot, auto-adds ticker to watchlist on buy, tracks it. Returns the trade dict. Raises `portfolio.service.TradeError(message)` on failure. Error message formats (the chat UI shows them verbatim after `✗ Buy 10 AAPL — `):
  - `insufficient cash ($1,912.40 needed, $840.00 available)`
  - `insufficient shares (10 requested, 4 held)`
  - `no price available for XYZ`
  - `quantity must be positive`
- `portfolio.service.get_portfolio() -> dict` — shape of `GET /api/portfolio` below.
- `watchlist.service.add(ticker) -> bool`, `remove(ticker) -> bool`, `list_items() -> list[dict]`.

### `llm` (llm-engineer)
- `llm/routes.py` exposes `router = APIRouter()` with `GET /api/chat` and `POST /api/chat`; `app/main.py` includes it.
- `llm.service.llm_available() -> bool` — `LLM_MOCK=true` or `OPENROUTER_API_KEY` non-empty.
- Model: `openrouter/@preset/finy` via `litellm.acompletion`, structured output (Pydantic `response_format`).
- Env loading: `app/main.py` calls `load_dotenv(<project root>/.env)` at import; nobody else loads .env.

## HTTP API (all JSON, same origin)

Tickers are uppercased server-side. Errors use FastAPI's `{"detail": "..."}`.

| Method & path | Request | Response |
|---|---|---|
| `GET /api/health` | — | `{"status": "ok", "llm_available": bool}` |
| `GET /api/stream/prices` | — | SSE; each `data:` line is a JSON **array** of `PriceUpdate` (changed tickers only); `: keepalive` every ~15s. Default event type (use `onmessage`). |
| `GET /api/portfolio` | — | `{"cash", "total_value", "unrealized_pnl", "positions": [{"ticker", "quantity", "avg_cost", "current_price", "market_value", "unrealized_pnl", "pnl_pct"}]}` |
| `POST /api/portfolio/trade` | `{"ticker", "quantity", "side": "buy"\|"sell"}` | 200 `{"trade": {...}, "portfolio": {...}}`; 400 `{"detail": "<TradeError message>"}` |
| `GET /api/portfolio/history?limit=200` | — | `[{"total_value", "recorded_at"}]` oldest first |
| `GET /api/trades?limit=50` | — | `[{"id", "ticker", "side", "quantity", "price", "executed_at"}]` newest first |
| `GET /api/watchlist` | — | `[{"ticker", "price", "previous_price", "open_price", "direction", "timestamp"}]` (price fields null until first tick) |
| `POST /api/watchlist` | `{"ticker"}` | 201 with the item; 409 if already present; 422 if ticker not `^[A-Z][A-Z0-9.\-]{0,9}$` |
| `DELETE /api/watchlist/{ticker}` | — | 204; 404 if absent |
| `GET /api/chat?limit=50` | — | `[ChatMessage]` oldest first |
| `POST /api/chat` | `{"message"}` | 200 `ChatMessage` (the assistant reply); 503 if LLM unavailable; 502 if the LLM call fails |

`ChatMessage` = `{"id", "role": "user"|"assistant", "content", "actions": [Action] | null, "created_at"}`

`Action` = `{"type": "trade"|"watchlist", "ticker", "ok": bool, "text": str, ...}` where trade adds `side, quantity, price|null, error|null` and watchlist adds `action: "add"|"remove", error|null`. `text` is the ready-to-render notice, e.g. `✓ Bought 10 AAPL @ $191.24`, `✗ Buy 10 AAPL — insufficient cash ($1,912.40 needed, $840.00 available)`, `✓ Added PYPL to watchlist`, `✗ Remove XYZ from watchlist — not in watchlist`.

### LLM mock (`LLM_MOCK=true`) — deterministic, used by E2E
Case-insensitive rules on the user message, all matches applied:
- `buy <qty> <TICKER>` → trade buy; `sell <qty> <TICKER>` → trade sell
- `add <TICKER>` / `watch <TICKER>` → watchlist add; `remove <TICKER>` / `unwatch <TICKER>` → watchlist remove
- `message` is `Mock reply: <summary>` where summary lists the requested actions, or `Mock reply: I can help with your portfolio.` when none.

## Frontend ↔ E2E selectors (`data-testid`)

| testid | Element |
|---|---|
| `connection-status` | header dot; attribute `data-state="connected"\|"reconnecting"\|"disconnected"` |
| `header-total-value`, `header-cash` | header numbers, formatted `$10,000.00` |
| `watchlist-row-<TICKER>` | watchlist row (click selects the ticker) |
| `watchlist-price-<TICKER>`, `watchlist-change-<TICKER>` | price and Chg % cells; price cell gets class `flash-up`/`flash-down` briefly |
| `watchlist-add-input`, `watchlist-add-button`, `watchlist-remove-<TICKER>` | watchlist management |
| `main-chart` (with `data-ticker`) | selected-ticker chart |
| `trade-ticker`, `trade-quantity`, `trade-buy`, `trade-sell`, `trade-error` | trade bar |
| `positions-table`, `position-row-<TICKER>` | positions table |
| `heatmap`, `heatmap-cell-<TICKER>` (with `data-pnl="up"\|"down"\|"flat"`) | treemap |
| `pnl-chart` | P&L line chart |
| `chat-panel`, `chat-input`, `chat-send`, `chat-loading`, `chat-unavailable` | chat panel |
| `chat-message` (with `data-role`), `chat-action` (with `data-ok="true"\|"false"`) | chat history and inline notices |

## Docker
- Image: Node 20 slim builds `frontend/` → `dist/`; Python 3.12 slim + uv runs `backend/` at `/app/backend`, dist copied to `/app/backend/static`. `CMD` from `/app/backend`: `uv run --frozen uvicorn app.main:app --host 0.0.0.0 --port 8000` (or the venv's uvicorn directly).
- `app/main.py` mounts `backend/static` at `/` with SPA fallback **only if that dir exists** (local dev uses the Vite dev server, which proxies `/api` to `localhost:8000`).
- Container name `finally`, image `finally`, `-v <project>/db:/app/db`, `--env-file .env`, port 8000.
