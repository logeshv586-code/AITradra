import pytest

from brokers.broker_router import BrokerRouter, Order, OrderSide


@pytest.mark.asyncio
async def test_ccxt_selection_fails_closed_when_not_configured():
    router = BrokerRouter({"PAPER_TRADE_MODE": True, "CRYPTO_BROKER": "hyperliquid"})
    result = await router.execute(
        Order(ticker="BTC", side=OrderSide.BUY, qty=0.001, reference_price=50000),
        asset_class="crypto",
        venue="ccxt",
    )
    assert result["status"] == "REJECTED"
    assert "CCXT" in result["reason"]


@pytest.mark.asyncio
async def test_unknown_crypto_venue_is_rejected_not_rerouted():
    router = BrokerRouter({"PAPER_TRADE_MODE": True})
    result = await router.execute(
        Order(ticker="BTC", side=OrderSide.BUY, qty=0.001, reference_price=50000),
        asset_class="crypto",
        venue="unknown_exchange",
    )
    assert result["status"] == "REJECTED"
    assert result["requested_venue"] == "unknown_exchange"
