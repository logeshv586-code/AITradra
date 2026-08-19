from datetime import datetime, timedelta

import pytest

from brokers.broker_router import Order, OrderSide, OrderType
from brokers.customer_hyperliquid_broker import CustomerHyperliquidBroker
from gateway.cache import SmartCache
from gateway.scrapers.social_scraper import SocialScraper


class _FakeExchange:
    def __init__(self):
        self.closed = []
        self.opened = []

    def market_close(self, ticker, qty, price, slippage):
        self.closed.append((ticker, qty, price, slippage))
        return {"status": "ok", "response": {"data": {"statuses": [{"filled": {"oid": 42}}]}}}

    def update_leverage(self, leverage, ticker, cross):
        return None

    def market_open(self, ticker, is_buy, qty, price, slippage):
        self.opened.append((ticker, is_buy, qty, price, slippage))
        return {"status": "ok"}


class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, response):
        self.response = response
        self.headers = {}

    def get(self, *args, **kwargs):
        return self.response


def _manual_live_broker(monkeypatch):
    import brokers.customer_hyperliquid_broker as module

    monkeypatch.setattr(
        module,
        "get_execution_status",
        lambda *args, **kwargs: {"live_execution_allowed": True, "blockers": []},
    )
    broker = object.__new__(CustomerHyperliquidBroker)
    broker.private_key = "test-only-key"
    broker.exchange = _FakeExchange()
    return broker


@pytest.mark.asyncio
async def test_reduce_only_customer_close_does_not_require_reference_or_protection(monkeypatch):
    broker = _manual_live_broker(monkeypatch)

    async def forbidden_reference(*args, **kwargs):
        raise AssertionError("reduce-only exit must not request a market reference")

    monkeypatch.setattr(CustomerHyperliquidBroker, "_reference_price", forbidden_reference)

    result = await broker.place_order(
        Order(
            ticker="BTC",
            side=OrderSide.SELL,
            qty=0.01,
            order_type=OrderType.MARKET,
            reduce_only=True,
        )
    )

    assert result["status"] == "FILLED"
    assert result["reduce_only"] is True
    assert result["order_id"] == "42"
    assert broker.exchange.closed
    assert not broker.exchange.opened


@pytest.mark.asyncio
async def test_new_customer_entry_still_runs_protection_validation(monkeypatch):
    broker = _manual_live_broker(monkeypatch)

    async def reference(*args, **kwargs):
        return 100.0

    monkeypatch.setattr(CustomerHyperliquidBroker, "_reference_price", reference)
    monkeypatch.setattr(
        CustomerHyperliquidBroker,
        "_validate_protection",
        staticmethod(lambda order, price: "missing protection"),
    )

    result = await broker.place_order(
        Order(
            ticker="BTC",
            side=OrderSide.BUY,
            qty=0.01,
            order_type=OrderType.MARKET,
            reduce_only=False,
            reference_price=100.0,
        )
    )

    assert result["status"] == "REJECTED"
    assert result["reason"] == "missing protection"
    assert not broker.exchange.opened


def test_cache_metadata_reports_real_age_and_source(tmp_path):
    store = SmartCache(db_path=tmp_path / "cache.sqlite3")
    store.set("AAPL", "price", {"px": 100.0}, "unit-test-source")

    fresh = store.get_metadata("AAPL", "price")
    assert fresh["source"] == "unit-test-source"
    assert fresh["age_minutes"] is not None
    assert 0 <= fresh["age_minutes"] < 1

    old_ts = (datetime.now() - timedelta(hours=3)).isoformat()
    import sqlite3

    with sqlite3.connect(store.db_path) as conn:
        conn.execute(
            "UPDATE cache SET timestamp = ? WHERE key = ? AND data_type = ?",
            (old_ts, "AAPL", "price"),
        )

    stale = store.get_metadata("AAPL", "price")
    assert stale["age_minutes"] >= 179
    assert store.get_freshness_label("AAPL", "price").startswith("Cached 3h")


def test_social_scraper_normalizes_real_reddit_payload():
    scraper = SocialScraper()
    scraper.session = _FakeSession(
        _FakeResponse(
            payload={
                "data": {
                    "children": [
                        {"data": {"title": "AAPL looks bullish, buy the dip", "selftext": "long growth", "permalink": "/r/stocks/1"}},
                        {"data": {"title": "AAPL risk discussion", "selftext": "possible drop", "permalink": "/r/stocks/2"}},
                    ]
                }
            }
        )
    )

    result = scraper.get_sentiment("AAPL")
    assert result["source"] == "reddit"
    assert result["data_available"] is True
    assert result["is_estimated"] is False
    assert result["mentions"] == result["reddit_mentions_24h"] == 2
    assert -1.0 <= result["score"] <= 1.0
    assert result["bull_bear_ratio"] == "50% bull"


def test_social_scraper_provider_failure_is_not_fake_neutral():
    scraper = SocialScraper()
    scraper.session = _FakeSession(_FakeResponse(status_code=403))

    result = scraper.get_sentiment("AAPL")
    assert result["source"] == "none"
    assert result["data_available"] is False
    assert result["is_estimated"] is True
    assert result["mentions"] == 0
    assert result["bull_bear_ratio"] == "N/A"
    assert result["reddit_sentiment"] == "unavailable"
