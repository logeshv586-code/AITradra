from datetime import datetime, timedelta, timezone

import pytest

from gateway.live_price_session import LivePriceSession, LivePriceUnavailable


@pytest.mark.asyncio
async def test_strict_live_price_uses_one_provider_and_reuses_within_window(monkeypatch):
    session = LivePriceSession()
    calls = []
    connection = {"id": "primary", "name": "PrimaryLive", "provider": "custom_json"}

    monkeypatch.setattr(
        "gateway.live_price_session.customer_runtime.enabled_connections",
        lambda category: [connection, {"id": "backup", "name": "Backup", "provider": "custom_json"}],
    )

    async def fetch(selected, ticker):
        calls.append((selected["id"], ticker))
        return {"px": 101.25, "pct_chg": 0.5, "close": 101.25, "volume": 123}

    monkeypatch.setattr("gateway.live_price_session.connected_sources._price_from_connection", fetch)
    monkeypatch.setenv("LIVE_PRICE_VALIDITY_SECONDS", "120")

    first = await session.get("AAPL")
    second = await session.get("AAPL")

    assert calls == [("primary", "AAPL")]
    assert first["source_used"] == "connected:PrimaryLive"
    assert first["fallback_used"] is False
    assert first["decision_grade"] is True
    assert second["reused_within_validity_window"] is True
    assert second["freshness_seconds"] >= 0


@pytest.mark.asyncio
async def test_strict_live_price_refetches_after_expiry(monkeypatch):
    session = LivePriceSession()
    connection = {"id": "primary", "name": "PrimaryLive", "provider": "custom_json"}
    calls = []

    monkeypatch.setattr(
        "gateway.live_price_session.customer_runtime.enabled_connections",
        lambda category: [connection],
    )

    async def fetch(selected, ticker):
        calls.append(ticker)
        return {"px": 200 + len(calls), "pct_chg": 1.0, "close": 200 + len(calls)}

    monkeypatch.setattr("gateway.live_price_session.connected_sources._price_from_connection", fetch)

    first = await session.get("MSFT")
    session._cache["MSFT"]["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    second = await session.get("MSFT")

    assert len(calls) == 2
    assert first["px"] != second["px"]
    assert second["reused_within_validity_window"] is False


@pytest.mark.asyncio
async def test_strict_live_price_never_falls_back_to_second_provider(monkeypatch):
    session = LivePriceSession()
    primary = {"id": "primary", "name": "PrimaryLive", "provider": "custom_json"}
    backup = {"id": "backup", "name": "BackupLive", "provider": "custom_json"}
    calls = []

    monkeypatch.setattr(
        "gateway.live_price_session.customer_runtime.enabled_connections",
        lambda category: [primary, backup],
    )

    async def fail_primary(selected, ticker):
        calls.append(selected["id"])
        raise RuntimeError("provider down")

    monkeypatch.setattr("gateway.live_price_session.connected_sources._price_from_connection", fail_primary)

    with pytest.raises(LivePriceUnavailable):
        await session.get("AAPL", force_refresh=True)

    assert calls == ["primary"]


@pytest.mark.asyncio
async def test_strict_live_price_blocks_when_no_provider_is_configured(monkeypatch):
    session = LivePriceSession()
    monkeypatch.setattr(
        "gateway.live_price_session.customer_runtime.enabled_connections",
        lambda category: [],
    )

    with pytest.raises(LivePriceUnavailable):
        await session.get("AAPL")
