# Massive API — Reference and FinAlly Integration Design

Researched 2026-09-18 against the live docs at <https://massive.com/docs> and the
client source at <https://github.com/massive-com/client-python>. Where the prose docs
and the client source disagreed, the source won — every constant below was read out of
`massive/rest/__init__.py` and `massive/rest/models/`, not out of a docs page.

Massive is Polygon.io, rebranded on 30 October 2025. Existing keys, accounts and
`api.polygon.io` all still work; the new surface is `api.massive.com`.

---

## 1. Client facts

| | |
|---|---|
| PyPI package | `massive` (version 2.8.0 at time of writing) |
| Install | `uv add massive` |
| Python | `>=3.9,<4.0` |
| Import | `from massive import RESTClient` |
| Base URL | `https://api.massive.com` (`BASE` in `massive/rest/__init__.py`) |
| API key env var | `MASSIVE_API_KEY` (`ENV_KEY`) — read automatically by the constructor |
| Auth header | `Authorization: Bearer <key>`, set by the client |
| Concurrency | **Synchronous.** Built on `urllib3`; there is no async REST client |
| Defaults | `connect_timeout=10.0`, `read_timeout=10.0`, `retries=3`, `num_pools=10` |
| Built-in retry | status forcelist `413, 429, 499, 500, 502, 503, 504`, backoff factor `0.1` |

```python
from massive import RESTClient

client = RESTClient()                    # reads MASSIVE_API_KEY from the environment
client = RESTClient(api_key="...")       # or pass it explicitly
```

Constructing a client with no key and no env var raises `massive.exceptions.AuthError`
immediately — it does not wait for the first request.

> Do not confuse `massive` with `massive-api-client` on PyPI. The latter is an unrelated
> third-party async wrapper at version 0.0.4. The official package is `massive`.

---

## 2. Plan tiers — the constraint that drives the whole design

| Plan | Price | Rate limit | Data latency | Snapshot endpoints |
|---|---|---|---|---|
| **Basic** | free | **5 calls/min** | **End of day** | ✗ *"Stocks Basic \| Not included"* |
| Starter | $29/mo | unlimited | 15-minute delayed | ✓ |
| Developer | $79/mo | unlimited | 15-minute delayed | ✓ |
| Advanced | $199/mo | unlimited | **Real-time** | ✓ |

Two consequences that are easy to get wrong:

1. **A free key cannot call the snapshot endpoint at all.** It returns `403 NOT_AUTHORIZED`.
   The free tier is limited to the aggregate (bar) endpoints, at end-of-day recency.
2. **Only Advanced is genuinely real-time.** On Starter and Developer the snapshot steps
   roughly every 15 minutes no matter how fast you poll, so polling faster than the
   15-second floor buys nothing on any tier.

The rate limit is rarely the binding constraint, because both of the endpoints FinAlly
uses return *every* requested ticker in a single request.

---

## 3. Realtime prices — snapshots

### 3.1 Full Market Snapshot (the primary live endpoint)

```
GET /v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,GOOGL,MSFT
```

Query parameters:

| Param | Type | Notes |
|---|---|---|
| `tickers` | comma-separated list | Case-sensitive. Omit entirely to get all ~10,000 US tickers |
| `include_otc` | boolean | Defaults to `false` |

```python
snapshots = client.get_snapshot_all("stocks", tickers=["AAPL", "GOOGL", "MSFT"])
for snap in snapshots:
    print(snap.ticker, snap.last_trade.price, snap.day.open, snap.prev_day.close)
```

Signature (from `massive/rest/snapshot.py`):

```python
def get_snapshot_all(
    self,
    market_type: Union[str, SnapshotMarketType],
    tickers: Optional[Union[str, List[str]]] = None,
    params: Optional[Dict[str, Any]] = None,
    raw: bool = False,
    include_otc: Optional[bool] = False,
    options: Optional[RequestOptionBuilder] = None,
) -> Union[List[TickerSnapshot], HTTPResponse]
```

**`TickerSnapshot` attribute → JSON key mapping.** The client renames fields, so code
written against the raw JSON keys will silently read `None`:

| Attribute | JSON key | Type |
|---|---|---|
| `ticker` | `ticker` | `str` |
| `day` | `day` | `Agg` — today's bar so far |
| `min` | `min` | `MinuteSnapshot` — most recent minute bar |
| `prev_day` | `prevDay` | `Agg` — previous session's bar |
| `last_trade` | `lastTrade` | `LastTrade` |
| `last_quote` | `lastQuote` | `LastQuote` |
| `todays_change` | `todaysChange` | `float` |
| `todays_change_percent` | `todaysChangePerc` | `float` |
| `updated` | `updated` | `int` — **nanoseconds** |
| `fair_market_value` | `fmv` | `float` — Business plans only |

`Agg` exposes `open/high/low/close/volume/vwap/timestamp/transactions` from the
one-letter keys `o/h/l/c/v/vw/t/n`. `LastTrade` exposes `price` from `p` and
`sip_timestamp` from `t`.

**Timestamp units are not consistent across the payload** — `updated` and
`last_trade.sip_timestamp` are nanoseconds, while `min.t` is milliseconds. Dividing the
wrong one by 1e9 puts a price in 1970.

### 3.2 Unified Snapshot (`/v3/snapshot`)

A newer cross-asset endpoint. Accepts `ticker.any_of` (up to 250 symbols), returns a
`session` object with `change / change_percent / open / high / low / close / volume`, plus
`market_status` (`open`, `closed`, `early_trading`, `late_trading`) and a `next_url`
cursor. Python method: `list_universal_snapshots(type=..., ticker_any_of=[...])`.

FinAlly does not use it. It is paginated (`limit` defaults to 10, max 250), which makes the
poller more complex for no gain at ~10 tickers, and it carries the same plan restrictions.
It is the right choice if FinAlly ever tracks options or crypto alongside stocks.

### 3.3 Single ticker

`client.get_snapshot_ticker("stocks", "AAPL")` → one `TickerSnapshot`. Not used: one
grouped call already covers every tracked ticker.

---

## 4. End-of-day prices — aggregates

These are available on **every** plan including Basic, which makes them the free tier's
only usable price source.

### 4.1 Daily Market Summary — grouped daily bars (the free-tier endpoint)

```
GET /v2/aggs/grouped/locale/us/market/stocks/{date}
```

One request returns the daily OHLCV bar for **every** US ticker on that date.

```python
bars = client.get_grouped_daily_aggs("2026-09-17")
closes = {b.ticker: b.close for b in bars}
```

```python
def get_grouped_daily_aggs(
    self,
    date: Union[str, date],
    adjusted: Optional[bool] = None,
    params: Optional[Dict[str, Any]] = None,
    raw: bool = False,
    locale: str = "us",
    market_type: str = "stocks",
    include_otc: bool = False,
    options: Optional[RequestOptionBuilder] = None,
) -> Union[List[GroupedDailyAgg], HTTPResponse]
```

`GroupedDailyAgg` maps `ticker ← T`, `open ← o`, `high ← h`, `low ← l`, `close ← c`,
`volume ← v`, `vwap ← vw`, `timestamp ← t` (milliseconds), `transactions ← n`.

`date` must be a **trading day**. A weekend or market holiday returns
`resultsCount: 0` with a `200`, not an error — so the caller walks back day by day until
it gets results.

### 4.2 Previous Day Bar

```
GET /v2/aggs/ticker/{ticker}/prev
```

```python
prev = client.get_previous_close_agg("AAPL")   # -> PreviousCloseAgg
```

`PreviousCloseAgg` maps `ticker ← T`, `close ← c`, `high ← h`, `low ← l`, `open ← o`,
`timestamp ← t`, `volume ← v`, `vwap ← vw`. One ticker per call, so it is only a
single-symbol fallback — ten tickers would be ten calls and blow the free tier's 5/min cap.

### 4.3 Daily Open/Close

`client.get_daily_open_close_agg(ticker, date)` → `DailyOpenCloseAgg`, which uniquely
includes `pre_market ← preMarket` and `after_hours ← afterHours`. Not used by FinAlly.

### 4.4 Custom bars

`client.list_aggs(ticker, multiplier, timespan, from_, to)` returns an iterator of `Agg`.
FinAlly's charts are session-scoped and built from the SSE stream (PLAN.md §10), so no
historical bars are fetched. This is the endpoint to reach for if that ever changes.

---

## 5. Errors

| Status | Meaning | FinAlly's response |
|---|---|---|
| 401 | Invalid or revoked key | Fall back to the pure simulator, log a warning |
| 403 | Plan does not include the endpoint | Classify the key as EOD-only (see §6.2) |
| 429 | Rate limit exceeded (Basic: 5/min) | Client retries automatically; then skip the cycle |
| 5xx | Server error | Client retries automatically; then skip the cycle |

The client raises `massive.exceptions.AuthError` and `BadResponse`. Its built-in retry
already covers 429 and 5xx with exponential backoff, so the poller adds no retry logic of
its own — it only decides what to do once the client has given up.

---

## 6. FinAlly integration design

### 6.1 Where this lives

The abstract `MarketDataSource` contract (`start / stop / add_ticker / remove_ticker /
get_tickers`, writing into the shared `PriceCache`) is unchanged. Everything below is
internal to `backend/app/market/massive_client.py` and `factory.py`, so the SSE layer,
the cache and the frontend stay agnostic about the source — as PLAN.md §6 requires.

### 6.2 Capability probe

Massive exposes no "what plan am I on?" endpoint, so the tier is discovered by trying.
At startup, one snapshot call for a single ticker classifies the key:

```python
class MassivePlan(Enum):
    LIVE = "live"          # snapshot endpoint works -> Starter, Developer or Advanced
    EOD_ONLY = "eod_only"  # 403 on snapshot          -> Basic (free)
    INVALID = "invalid"    # 401                      -> bad key


async def detect_plan(client: RESTClient) -> MassivePlan:
    """Classify the API key by attempting a one-ticker snapshot call."""
    try:
        await asyncio.to_thread(client.get_snapshot_all, "stocks", ["AAPL"])
        return MassivePlan.LIVE
    except AuthError:
        return MassivePlan.INVALID
    except BadResponse as exc:
        if "403" in str(exc) or "NOT_AUTHORIZED" in str(exc):
            return MassivePlan.EOD_ONLY
        raise
```

One call, once, at startup. Even on the free tier that leaves 4 of 5 calls in the minute.

### 6.3 Source selection

`create_market_data_source()` keeps its signature and gains the plan branch:

| Key | Plan | Source | Seed prices |
|---|---|---|---|
| absent | — | `SimulatorDataSource` | built-in table, or `last_prices` |
| present | `LIVE` | `MassiveDataSource` | n/a — real prices |
| present | `EOD_ONLY` | `SimulatorDataSource` | **real closes from `get_grouped_daily_aggs`** |
| present | `INVALID` | `SimulatorDataSource` | built-in table, logged warning |

The `EOD_ONLY` path is the interesting one. A free key still buys something real: one
grouped-daily call yields genuine closing prices for every tracked ticker, and those become
the simulator's starting point. The user sees real market levels that visibly move, instead
of a flat line at a stale close. It costs one call per startup.

```python
async def seed_from_eod(client: RESTClient, tickers: list[str]) -> dict[str, float]:
    """Real closing prices for the given tickers, from one grouped-daily call.

    Walks back from today to find the most recent trading day; a weekend or
    holiday returns an empty result set rather than an error.
    """
    day = date.today()
    for _ in range(5):
        bars = await asyncio.to_thread(client.get_grouped_daily_aggs, day.isoformat())
        if bars:
            wanted = set(tickers)
            return {b.ticker: b.close for b in bars if b.ticker in wanted}
        day -= timedelta(days=1)
    return {}
```

Tickers Massive has never heard of are simply absent from the mapping, and fall through to
the simulator's existing random-seed behaviour (PLAN.md §6, "Unknown tickers"). Adding a
ticker still never fails.

Seed precedence for the simulator is therefore: `last_prices` table → Massive EOD close →
built-in seed → generated random seed. Restart continuity wins over the EOD close, so a
position bought at a simulated price does not reprice against the real close and show a
phantom loss.

### 6.4 Normalization

One dataclass is the entire boundary between Massive's payload and the rest of FinAlly.
Nothing downstream ever sees a `TickerSnapshot`:

```python
@dataclass(frozen=True, slots=True)
class MassiveQuote:
    """One ticker's price, normalized from a Massive snapshot."""

    ticker: str
    price: float
    open: float        # real session open, from day.open
    prev_close: float  # from prev_day.close
    timestamp: float   # Unix seconds


def to_quote(snap: TickerSnapshot) -> MassiveQuote | None:
    """Map a snapshot to a quote, or None if it carries no usable price."""
    price = _first_price(snap)
    if price is None:
        return None
    return MassiveQuote(
        ticker=snap.ticker,
        price=price,
        open=snap.day.open if snap.day else price,
        prev_close=snap.prev_day.close if snap.prev_day else price,
        timestamp=snap.updated / 1e9 if snap.updated else time.time(),
    )


def _first_price(snap: TickerSnapshot) -> float | None:
    """last trade, else the latest minute bar's close, else today's close."""
    if snap.last_trade and snap.last_trade.price:
        return snap.last_trade.price
    if snap.min and snap.min.close:
        return snap.min.close
    if snap.day and snap.day.close:
        return snap.day.close
    return None
```

Three notes on that mapping:

- **`last_trade` is not always present.** It is plan-gated and absent outside market hours
  for thinly traded names, hence the fallback chain rather than a direct attribute read.
- **`open` is the real session open**, not "the first price the cache happened to see".
  PLAN.md §6 defines the session open that way because the simulator has no trading day;
  in Massive mode the genuine `day.open` is available and is a strictly better reference
  for the watchlist's Chg % column. The cache stores it identically either way.
- **`updated` is nanoseconds**, so it is divided by 1e9, not 1e3.

### 6.5 Polling

```python
POLL_SECONDS = 15.0
```

A single constant, not a new environment variable — PLAN.md §5 fixes the env surface, and
no tier rewards a faster poll. Paid tiers have no rate limit, and Starter/Developer data
only moves every 15 minutes, so 15 seconds is already faster than the data changes on every
plan but Advanced.

The loop mirrors the simulator's: read the tracked ticker set, make **one** grouped call,
write each quote to the `PriceCache`, sleep. Never loop per ticker — ten tickers at 15s
would be 40 calls/min, which is rate-limited on Basic and pointless everywhere else.

```python
async def _poll_loop(self) -> None:
    while True:
        tickers = self.get_tickers()
        if tickers:
            try:
                snaps = await asyncio.to_thread(
                    self._client.get_snapshot_all, "stocks", tickers
                )
                for snap in snaps:
                    if quote := to_quote(snap):
                        self._cache.update(quote)
            except BadResponse:
                logger.warning("Massive poll failed; keeping previous prices")
        await asyncio.sleep(POLL_SECONDS)
```

Every `RESTClient` call is wrapped in `asyncio.to_thread`, because the client is
synchronous urllib3 and a blocking 10-second read timeout on the event loop would stall
every open SSE connection at once.

A failed cycle leaves the cache untouched. Since the SSE stream only emits tickers whose
price changed (PLAN.md §6), an outage degrades to silence on the wire and stale-but-correct
prices on screen, rather than an error or a gap.

### 6.6 Testing

Recorded JSON fixtures, no live calls in CI — the free tier's 5/min cap makes a test suite
that hits the network flaky by construction.

- `to_quote` maps a full snapshot correctly, including the nanosecond division
- `_first_price` falls through `last_trade` → `min` → `day`, and returns `None` when empty
- `detect_plan` returns `LIVE` / `EOD_ONLY` / `INVALID` for 200 / 403 / 401
- `seed_from_eod` walks back past an empty weekend result and filters to tracked tickers
- the factory selects the right source for each of the four key/plan combinations
- a `BadResponse` mid-poll leaves the cache unchanged and does not kill the loop

---

## 7. Known caveats

- **Free keys never show live movement from Massive itself.** The EOD seed makes the
  opening prices real; the motion after that is simulated. This is stated in the startup
  log so it is never mistaken for live data.
- **Starter and Developer are 15-minute delayed.** Real, but visibly behind. Only Advanced
  is real-time.
- **Snapshot data is cleared daily at 3:30 AM EST** and repopulates from about 4:00 AM EST
  as exchanges report. A poll in that window can return snapshots with no `day` bar — the
  `_first_price` fallback chain covers it.
- **Tickers are case-sensitive** in both `tickers=` and `ticker.any_of`.
- **`api.polygon.io` still works** and returns identical payloads, but new work should
  target `api.massive.com`, which is the client's default.

---

## Sources

- [Massive API docs](https://massive.com/docs)
- [Full Market Snapshot](https://massive.com/docs/rest/stocks/snapshots/full-market-snapshot)
- [Unified Snapshot](https://massive.com/docs/rest/stocks/snapshots/unified-snapshot)
- [Daily Market Summary](https://massive.com/docs/rest/stocks/aggregates/daily-market-summary)
- [Previous Day Bar](https://massive.com/docs/rest/stocks/aggregates/previous-day-bar)
- [Massive pricing](https://massive.com/pricing)
- [massive-com/client-python](https://github.com/massive-com/client-python)
- [Polygon.io is Now Massive](https://massive.com/blog/polygon-is-now-massive)
