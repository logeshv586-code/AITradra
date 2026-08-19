from types import SimpleNamespace

from core.trading_safety import LIVE_ACK_PHRASE, get_execution_status
from gateway.connected_source_adapter import _dig
from gateway.customer_runtime import CustomerRuntimeStore, DEFAULT_HISTORY_USER


def _settings(**overrides):
    values = {
        "PAPER_TRADE_MODE": True,
        "AUTOTRADE_ENABLED": False,
        "MANUAL_LIVE_TRADING_ENABLED": False,
        "HYPERLIQUID_PRIVATE_KEY": None,
        "LIVE_TRADING_ACK": "",
        "REQUIRE_PROTECTIVE_ORDERS": True,
        "REQUIRE_STRATEGY_VALIDATION": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_customer_connection_secrets_are_encrypted_and_never_listed(tmp_path):
    store = CustomerRuntimeStore(
        db_path=tmp_path / "customer.sqlite3",
        key_path=tmp_path / ".customer.key",
    )
    created = store.save_connection(
        name="My Market API",
        category="market_data",
        provider="custom_json",
        config={"endpoint": "https://example.invalid/{ticker}"},
        secrets={"api_key": "super-secret-customer-key"},
    )

    assert created["has_credentials"] is True
    assert "secrets" not in created
    listed = store.list_connections()
    assert len(listed) == 1
    assert listed[0]["has_credentials"] is True
    assert "secrets" not in listed[0]

    hydrated = store.get_connection(created["id"], include_secrets=True)
    assert hydrated["secrets"]["api_key"] == "super-secret-customer-key"

    raw_db = (tmp_path / "customer.sqlite3").read_bytes()
    assert b"super-secret-customer-key" not in raw_db


def test_history_uses_single_default_customer_profile(tmp_path):
    store = CustomerRuntimeStore(
        db_path=tmp_path / "customer.sqlite3",
        key_path=tmp_path / ".customer.key",
    )
    record = store.record_history(
        event_type="research",
        ticker="AAPL",
        title="Researched AAPL",
        details={"recommendation": "HOLD"},
    )
    assert record["user_id"] == DEFAULT_HISTORY_USER == "default"
    history = store.get_history(ticker="AAPL")
    assert history[0]["user_id"] == "default"
    assert history[0]["ticker"] == "AAPL"


def test_manual_live_permission_is_separate_from_autonomous_trading():
    config = _settings(
        PAPER_TRADE_MODE=False,
        MANUAL_LIVE_TRADING_ENABLED=True,
        AUTOTRADE_ENABLED=False,
        LIVE_TRADING_ACK=LIVE_ACK_PHRASE,
    )

    manual = get_execution_status(
        config,
        purpose="manual",
        has_private_key=True,
    )
    automated = get_execution_status(
        config,
        purpose="automation",
        has_private_key=True,
    )

    assert manual["live_execution_allowed"] is True
    assert manual["manual_live_enabled"] is True
    assert automated["live_execution_allowed"] is False
    assert any("AUTOTRADE_ENABLED" in blocker for blocker in automated["blockers"])


def test_adding_a_broker_key_does_not_unlock_manual_live_by_itself():
    status = get_execution_status(
        _settings(),
        purpose="manual",
        has_private_key=True,
    )
    assert status["live_execution_allowed"] is False
    assert status["paper_mode"] is True
    assert any("PAPER_TRADE_MODE" in blocker for blocker in status["blockers"])
    assert any("MANUAL_LIVE_TRADING_ENABLED" in blocker for blocker in status["blockers"])


def test_custom_json_mapping_supports_nested_price_and_news_fields():
    payload = {
        "data": {
            "quote": {"price": 123.45, "change": 1.25},
            "articles": [
                {"title": "Example headline", "meta": {"source": "Example News"}}
            ],
        }
    }
    assert _dig(payload, "data.quote.price") == 123.45
    assert _dig(payload, "data.quote.change") == 1.25
    assert _dig(payload, "data.articles.0.title") == "Example headline"
    assert _dig(payload, "data.articles.0.meta.source") == "Example News"
