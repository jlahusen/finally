"""Price cache semantics, the simulator source and the changed-only SSE tick."""

from market.cache import PriceCache
from market.source import SimulatorSource
from market.stream import changed_updates


def test_update_tracks_previous_open_and_direction():
    cache = PriceCache()
    first = cache.update("AAPL", 190.0)
    assert (first.previous_price, first.open_price, first.direction) == (190.0, 190.0, "flat")
    second = cache.update("AAPL", 191.234)
    assert (second.price, second.previous_price, second.open_price, second.direction) == (191.23, 190.0, 190.0, "up")
    assert cache.update("AAPL", 189.0).direction == "down"
    assert second.timestamp.endswith("Z")


def test_explicit_open_price_wins():
    cache = PriceCache()
    assert cache.update("AAPL", 190.0, open_price=185.0).open_price == 185.0


def test_track_untrack():
    cache = PriceCache()
    cache.track("aapl")
    cache.update("AAPL", 1.0)
    assert cache.tracked() == ["AAPL"]
    cache.untrack("AAPL")
    assert cache.tracked() == [] and cache.get("AAPL") is None


async def test_tracked_unknown_ticker_priced_within_one_tick():
    cache = PriceCache()
    source = SimulatorSource(cache)
    cache.track("ZZZZ")
    await source.tick()
    assert cache.get("ZZZZ").price > 0
    cache.untrack("ZZZZ")
    await source.tick()
    assert cache.get("ZZZZ") is None


async def test_simulator_source_resumes_from_last_prices():
    cache = PriceCache()
    source = SimulatorSource(cache, seeds={"AAPL": 250.0})
    cache.track("AAPL")
    await source.tick()
    assert cache.get("AAPL").open_price == 250.0
    assert abs(cache.get("AAPL").price - 250.0) < 250.0 * 0.06


def test_changed_updates_emits_only_changes():
    cache = PriceCache()
    sent: dict[str, float] = {}
    cache.update("AAPL", 190.0)
    cache.update("MSFT", 420.0)
    assert {u["ticker"] for u in changed_updates(cache, sent)} == {"AAPL", "MSFT"}
    assert changed_updates(cache, sent) == []
    cache.update("AAPL", 191.0)
    cache.update("MSFT", 420.0)
    changed = changed_updates(cache, sent)
    assert [u["ticker"] for u in changed] == ["AAPL"]
    assert set(changed[0]) == {"ticker", "price", "previous_price", "open_price", "direction", "timestamp"}


async def test_track_seeds_price_immediately_and_tick_continues_from_it():
    cache = PriceCache()
    source = SimulatorSource(cache, seeds={"PYPL": 70.0})
    cache.track("PYPL")
    assert cache.get("PYPL").price == 70.0
    await source.tick()
    assert cache.get("PYPL").open_price == 70.0
    assert cache.get("PYPL").previous_price == 70.0


def test_track_without_seeder_waits_for_tick():
    cache = PriceCache()
    cache.track("PYPL")
    assert cache.get("PYPL") is None
