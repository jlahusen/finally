"""Execute the assistant's requested actions and describe each outcome as an `Action` dict."""

from llm.mock import format_quantity
from llm.schema import LLMResponse, TradeRequest, WatchlistChange
from portfolio import service as portfolio_service
from watchlist import service as watchlist_service


def run_trade(request: TradeRequest) -> dict:
    """Execute one trade; a `TradeError` becomes a failed action carrying its message."""
    ticker = request.ticker.upper()
    qty = format_quantity(request.quantity)
    action = {"type": "trade", "ticker": ticker, "side": request.side, "quantity": request.quantity}
    try:
        trade = portfolio_service.execute_trade(ticker, request.side, request.quantity)
    except portfolio_service.TradeError as error:
        text = f"✗ {request.side.capitalize()} {qty} {ticker} — {error}"
        return {**action, "ok": False, "price": None, "error": str(error), "text": text}
    verb = "Bought" if request.side == "buy" else "Sold"
    text = f"✓ {verb} {qty} {ticker} @ ${trade['price']:,.2f}"
    return {**action, "ok": True, "price": trade["price"], "error": None, "text": text}


def run_watchlist_change(change: WatchlistChange) -> dict:
    """Apply one watchlist add/remove; a no-op (already present / absent) is a failed action."""
    ticker = change.ticker.upper()
    action = {"type": "watchlist", "ticker": ticker, "action": change.action}
    if change.action == "add":
        ok = watchlist_service.add(ticker)
        done, attempt, error = f"Added {ticker} to", f"Add {ticker} to", "already in watchlist"
    else:
        ok = watchlist_service.remove(ticker)
        done, attempt, error = f"Removed {ticker} from", f"Remove {ticker} from", "not in watchlist"
    if ok:
        return {**action, "ok": True, "error": None, "text": f"✓ {done} watchlist"}
    return {**action, "ok": False, "error": error, "text": f"✗ {attempt} watchlist — {error}"}


def run_actions(response: LLMResponse) -> list[dict]:
    """Run all trades, then all watchlist changes, in order; never stops on a failure."""
    return [run_trade(t) for t in response.trades] + [
        run_watchlist_change(c) for c in response.watchlist_changes
    ]
