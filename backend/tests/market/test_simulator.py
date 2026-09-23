"""Simulator GBM math, seeding and correlation."""

import math

import numpy as np

from market import simulator as sim
from market.seeds import PROFILES
from market.simulator import Simulator


def test_step_produces_positive_finite_prices():
    s = Simulator(rng=np.random.default_rng(1))
    for ticker in PROFILES:
        s.add(ticker)
    for _ in range(1000):
        prices = s.step()
    assert set(prices) == set(PROFILES)
    assert all(p > 0 and math.isfinite(p) for p in prices.values())


def test_gbm_log_returns_match_volatility(monkeypatch):
    monkeypatch.setattr(sim, "EVENT_PROBABILITY", 0.0)
    s = Simulator(rng=np.random.default_rng(2))
    s.add("AAPL")
    prices = [s.add("AAPL")] + [s.step()["AAPL"] for _ in range(20000)]
    returns = np.diff(np.log(prices))
    expected = PROFILES["AAPL"].volatility * math.sqrt(sim.DT)
    assert abs(returns.std() / expected - 1) < 0.05


def test_same_sector_tickers_are_correlated(monkeypatch):
    monkeypatch.setattr(sim, "EVENT_PROBABILITY", 0.0)
    s = Simulator(rng=np.random.default_rng(3))
    s.add("AAPL")
    s.add("MSFT")
    series = [s.step() for _ in range(5000)]
    aapl = np.diff(np.log([p["AAPL"] for p in series]))
    msft = np.diff(np.log([p["MSFT"] for p in series]))
    assert np.corrcoef(aapl, msft)[0, 1] > 0.4


def test_events_jump_two_to_five_percent(monkeypatch):
    monkeypatch.setattr(sim, "EVENT_PROBABILITY", 1.0)
    factors = [Simulator(rng=np.random.default_rng(i))._event_factor() for i in range(50)]
    assert all(0.02 <= abs(f - 1) <= 0.05 for f in factors)


def test_seed_precedence_and_unknown_ticker():
    s = Simulator(seeds={"AAPL": 250.0})
    assert s.add("AAPL") == 250.0
    assert s.add("MSFT") == PROFILES["MSFT"].price
    unknown = s.add("ZZZZ")
    assert 20 <= unknown <= 400


def test_remove_stops_simulating():
    s = Simulator()
    s.add("AAPL")
    s.remove("AAPL")
    assert s.step() == {}
