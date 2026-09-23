"""System prompt, portfolio context and message-list construction."""

SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant inside a simulated trading workstation.
The user trades a virtual portfolio with fake money; market orders fill instantly at the current price.

Your job:
- Analyze portfolio composition, risk concentration and P&L.
- Suggest trades with brief reasoning.
- Execute trades when the user asks or agrees, by listing them in `trades`.
- Manage the watchlist proactively via `watchlist_changes`.
- Be concise and data-driven.

Only propose trades you expect to pass validation: buys need enough cash, sells need enough shares held.
Fractional quantities are allowed. Any ticker symbol may be traded or watched.
The app reports the outcome of each action to the user itself, so do not claim an action succeeded.

Always respond with JSON matching the schema: `message` (your reply), `trades` and `watchlist_changes`
(use empty lists when there is nothing to do)."""


def _money(value: float | None) -> str:
    return "n/a" if value is None else f"${value:,.2f}"


def build_context(portfolio: dict, watchlist: list[dict]) -> str:
    """Render cash, positions with P&L, watchlist prices and total value as plain text."""
    lines = [
        f"Cash: {_money(portfolio['cash'])}",
        f"Total portfolio value: {_money(portfolio['total_value'])}",
        f"Unrealized P&L: {_money(portfolio['unrealized_pnl'])}",
        "Positions:",
    ]
    lines += [
        f"- {p['ticker']}: {p['quantity']} shares, avg cost {_money(p['avg_cost'])}, "
        f"price {_money(p['current_price'])}, value {_money(p['market_value'])}, "
        f"P&L {_money(p['unrealized_pnl'])} ({p['pnl_pct']:.2f}%)"
        for p in portfolio["positions"]
    ] or ["- none"]
    lines.append("Watchlist:")
    lines += [f"- {w['ticker']}: {_money(w['price'])}" for w in watchlist] or ["- empty"]
    return "\n".join(lines)


def history_entry(message: dict) -> dict:
    """Convert a stored chat message to an LLM message, appending action outcomes for assistants."""
    content = message["content"]
    if message["actions"]:
        content += "\n" + "\n".join(action["text"] for action in message["actions"])
    return {"role": message["role"], "content": content}


def build_messages(context: str, history: list[dict], user_message: str) -> list[dict]:
    """Assemble system prompt, current portfolio context, prior conversation and the new message."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Current portfolio state:\n{context}"},
        *(history_entry(m) for m in history),
        {"role": "user", "content": user_message},
    ]
