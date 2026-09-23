"""Massive parsing, plan probe, EOD seeding, polling and source selection, via httpx MockTransport."""

from datetime import date

import httpx

from market import factory
from market.cache import PriceCache
from market.massive import MassivePlan, MassiveSource, detect_plan, fetch_eod_closes, parse_snapshot
from market.source import SimulatorSource

SNAPSHOT = {
    "ticker": "AAPL",
    "day": {"o": 189.5, "c": 190.9},
    "min": {"c": 191.0, "t": 1757845862000},
    "prevDay": {"c": 188.0},
    "lastTrade": {"p": 191.24, "t": 1757845862512000000},
    "updated": 1757845862512000000,
}


def client_for(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url="https://api.massive.com", transport=httpx.MockTransport(handler))


def test_parse_snapshot_full():
    ticker, price, day_open, ts = parse_snapshot(SNAPSHOT)
    assert (ticker, price, day_open) == ("AAPL", 191.24, 189.5)
    assert abs(ts - 1757845862.512) < 1e-3


def test_parse_snapshot_price_fallbacks():
    no_trade = {**SNAPSHOT, "lastTrade": None}
    assert parse_snapshot(no_trade)[1] == 191.0
    only_day = {"ticker": "AAPL", "day": {"o": 189.5, "c": 190.9}}
    assert parse_snapshot(only_day)[1:3] == (190.9, 189.5)
    assert parse_snapshot({"ticker": "AAPL", "day": {}}) is None


async def test_detect_plan_by_status():
    for status, plan in [(200, MassivePlan.LIVE), (403, MassivePlan.EOD_ONLY), (401, MassivePlan.INVALID)]:
        client = client_for(lambda req, s=status: httpx.Response(s, json={"tickers": []}))
        assert await detect_plan(client) is plan


async def test_fetch_eod_walks_back_past_empty_days():
    seen = []

    def handler(request):
        seen.append(request.url.path.rsplit("/", 1)[-1])
        if len(seen) < 3:
            return httpx.Response(200, json={"resultsCount": 0})
        return httpx.Response(200, json={"results": [{"T": "AAPL", "c": 191.0}, {"T": "XYZ", "c": 1.0}]})

    closes = await fetch_eod_closes(client_for(handler), ["AAPL", "MSFT"], today=date(2026, 9, 21))
    assert closes == {"AAPL": 191.0}
    assert seen == ["2026-09-20", "2026-09-19", "2026-09-18"]


async def test_poll_writes_cache_with_real_open():
    requested = []

    def handler(request):
        requested.append(request.url.params["tickers"])
        return httpx.Response(200, json={"tickers": [SNAPSHOT]})

    cache = PriceCache()
    cache.track("AAPL")
    cache.track("MSFT")
    await MassiveSource(cache, client_for(handler)).tick()
    assert requested == ["AAPL,MSFT"]
    assert (cache.get("AAPL").price, cache.get("AAPL").open_price) == (191.24, 189.5)


async def test_poll_failure_keeps_previous_prices():
    cache = PriceCache()
    cache.track("AAPL")
    cache.update("AAPL", 190.0)
    await MassiveSource(cache, client_for(lambda r: httpx.Response(500))).tick()
    assert cache.get("AAPL").price == 190.0


async def test_factory_without_key_uses_simulator(monkeypatch):
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    source = await factory.create_source(PriceCache(), {"AAPL": 250.0}, ["AAPL"])
    assert isinstance(source, SimulatorSource)
    assert source.simulator.add("AAPL") == 250.0


async def test_factory_branches_on_plan():
    def handler(request):
        if "snapshot" in request.url.path:
            return httpx.Response(403)
        return httpx.Response(200, json={"results": [{"T": "AAPL", "c": 191.0}, {"T": "MSFT", "c": 430.0}]})

    cache = PriceCache()
    cache.track("AAPL")
    cache.track("MSFT")
    source = await factory._source_for_key(cache, {"MSFT": 999.0}, ["AAPL", "MSFT"], client_for(handler))
    assert isinstance(source, SimulatorSource)
    assert source.simulator.add("AAPL") == 191.0
    assert source.simulator.add("MSFT") == 999.0

    invalid = await factory._source_for_key(cache, {}, [], client_for(lambda r: httpx.Response(401)))
    assert isinstance(invalid, SimulatorSource)

    live = await factory._source_for_key(cache, {}, [], client_for(lambda r: httpx.Response(200, json={"tickers": []})))
    assert isinstance(live, MassiveSource)


async def test_factory_falls_back_to_simulator_when_massive_unreachable():
    def unreachable(request):
        raise httpx.ConnectError("no route to host", request=request)

    def timing_out(request):
        raise httpx.ReadTimeout("timed out", request=request)

    for handler in (unreachable, timing_out):
        source = await factory._source_for_key(PriceCache(), {"AAPL": 250.0}, ["AAPL"], client_for(handler))
        assert isinstance(source, SimulatorSource)
        assert source.simulator.add("AAPL") == 250.0
