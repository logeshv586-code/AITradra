"""Tests for the PaperBroker: real-price fills, honest P&L, restart survival."""

import asyncio
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _swap_knowledge_store(tmp_dir):
    from gateway import knowledge_store as ks_module
    from gateway.knowledge_store import KnowledgeStore
    store = KnowledgeStore(db_path=os.path.join(tmp_dir, "test.db"))
    original = ks_module.knowledge_store
    ks_module.knowledge_store = store
    return store, original


def _seed_price(store, ticker, close, date="2026-07-22"):
    store.store_daily_ohlcv(ticker, [{
        "date": date, "open": close - 1, "high": close + 1,
        "low": close - 2, "close": close, "volume": 1_000_000,
    }])


class TestPaperBroker:
    def test_fills_at_stored_market_price(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, original = _swap_knowledge_store(tmp)
            try:
                _seed_price(store, "AAPL", 210.50)
                from brokers.broker_router import PaperBroker, Order, OrderSide, OrderType
                broker = PaperBroker()
                fill = asyncio.run(broker.place_order(
                    Order(ticker="AAPL", side=OrderSide.BUY, qty=10, order_type=OrderType.MARKET)))
                assert fill["status"] == "FILLED"
                assert fill["fill_price"] == 210.50
            finally:
                from gateway import knowledge_store as ks_module
                ks_module.knowledge_store = original

    def test_rejects_order_with_no_known_price(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, original = _swap_knowledge_store(tmp)
            try:
                from brokers.broker_router import PaperBroker, Order, OrderSide, OrderType
                broker = PaperBroker()
                result = asyncio.run(broker.place_order(
                    Order(ticker="UNKNOWN", side=OrderSide.BUY, qty=1, order_type=OrderType.MARKET)))
                assert result["status"] == "REJECTED"
                assert "No market price" in result["reason"]
            finally:
                from gateway import knowledge_store as ks_module
                ks_module.knowledge_store = original

    def test_realized_pnl_and_win_rate(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, original = _swap_knowledge_store(tmp)
            try:
                from brokers.broker_router import PaperBroker, Order, OrderSide, OrderType
                _seed_price(store, "NVDA", 100.0, date="2026-07-20")
                broker = PaperBroker()
                asyncio.run(broker.place_order(
                    Order(ticker="NVDA", side=OrderSide.BUY, qty=50, order_type=OrderType.MARKET)))
                # Price rises → sell at profit
                _seed_price(store, "NVDA", 110.0, date="2026-07-21")
                sell = asyncio.run(broker.place_order(
                    Order(ticker="NVDA", side=OrderSide.SELL, qty=50, order_type=OrderType.MARKET)))
                assert sell["realized_pnl"] == pytest.approx(500.0)
                bal = asyncio.run(broker.get_balance())
                assert bal["realized_pnl"] == pytest.approx(500.0)
                assert bal["equity"] == pytest.approx(100_500.0)
                assert bal["win_rate"] == 1.0
            finally:
                from gateway import knowledge_store as ks_module
                ks_module.knowledge_store = original

    def test_cannot_sell_more_than_held(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, original = _swap_knowledge_store(tmp)
            try:
                from brokers.broker_router import PaperBroker, Order, OrderSide, OrderType
                _seed_price(store, "TSLA", 300.0)
                broker = PaperBroker()
                result = asyncio.run(broker.place_order(
                    Order(ticker="TSLA", side=OrderSide.SELL, qty=5, order_type=OrderType.MARKET)))
                assert result["status"] == "REJECTED"
            finally:
                from gateway import knowledge_store as ks_module
                ks_module.knowledge_store = original

    def test_state_survives_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, original = _swap_knowledge_store(tmp)
            try:
                from brokers.broker_router import PaperBroker, Order, OrderSide, OrderType
                _seed_price(store, "MSFT", 400.0)
                broker = PaperBroker()
                asyncio.run(broker.place_order(
                    Order(ticker="MSFT", side=OrderSide.BUY, qty=10, order_type=OrderType.MARKET)))
                # Fresh instance replays persisted trades
                broker2 = PaperBroker()
                bal = asyncio.run(broker2.get_balance())
                assert bal["trade_count"] == 1
                assert bal["cash"] == pytest.approx(100_000.0 - 4_000.0)
                positions = asyncio.run(broker2.get_positions())
                assert positions[0]["ticker"] == "MSFT"
                assert positions[0]["qty"] == 10
            finally:
                from gateway import knowledge_store as ks_module
                ks_module.knowledge_store = original


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
