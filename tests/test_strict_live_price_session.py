from datetime import datetime, timedelta, timezone

import pytest

from gateway.live_price_session import LivePriceSession, LivePriceUnavailable


@pytest.mark.asyncio
async def test_strict_live_price_reuses_validated_observation_within_window(monkeypatch):
    session = LivePriceSession()
    primary = {"id": "primary", "name": "PrimaryLive", "provider": "custom_json"}
    verifier = {"id": "verify", "name": "VerifierLive", "provider": "custom_json"}
    calls = []
    monkeypatch.setattr(
        "gateway.live_price_session.customer_runtime.enabled_connections",
        lambda category: [primary, verifier],
    )

    async def fetch(selected, ticker):
        calls.append((selected["id"], ticker))
        price = 101.25 if selected["id"] == "primary" else 101.20
        return {"px": price, "pct_chg": 0.5, "close": price, "volume": 123}

    monkeypatch.setattr("gateway.live_price_session.connected_sources._price_from_connection", fetch)
    monkeypatch.setenv("LIVE_PRICE_VALIDITY_SECONDS", "120")
    monkeypatch.setenv("LIVE_PRICE_REQUIRE_CROSSCHECK", "true")

    first = await session.get("AAPL")
    second = await session.get("AAPL")

    assert calls == [("primary", "AAPL"), ("verify", "AAPL")]
    assert first["source_used"] == "connected:PrimaryLive"
    assert first["fallback_used"] is False
    assert first["decision_grade"] is True
    assert first["crosscheck"]["performed"] is True
    assert first["crosscheck"]["eligible"] is True
    assert second["reused_within_validity_window"] is True


@pytest.mark.asyncio
async def test_strict_live_price_refetches_after_expiry(monkeypatch):
    session = LivePriceSession()
    primary = {"id": "primary", "name": "PrimaryLive", "provider": "custom_json"}
    monkeypatch.setattr(
        "gateway.live_price_session.customer_runtime.enabled_connections",
        lambda category: [primary],
    )
    monkeypatch.setenv("LIVE_PRICE_REQUIRE_CROSSCHECK", "false")
    calls = []

    async def fetch(selected, ticker):
        calls.append(ticker)
        price = 200 + len(calls)
        return {"px": price, "pct_chg": 1.0, "close": price}

    monkeypatch.setattr("gateway.live_price_session.connected_sources._price_from_connection", fetch)
    first = await session.get("MSFT")
    session._cache["MSFT"]["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    second = await session.get("MSFT")

    assert len(calls) == 2
    assert first["px"] != second["px"]
    assert second["reused_within_validity_window"] is False


@pytest.mark.asyncio
async def test_primary_failure_never_uses_verifier_as_fallback(monkeypatch):
    session = LivePriceSession()
    primary = {"id": "primary", "name": "PrimaryLive", "provider": "custom_json"}
    verifier = {"id": "verify", "name": "VerifierLive", "provider": "custom_json"}
    calls = []
    monkeypatch.setattr(
        "gateway.live_price_session.customer_runtime.enabled_connections",
        lambda category: [primary, verifier],
    )

    async def fetch(selected, ticker):
        calls.append(selected["id"])
        if selected["id"] == "primary":
            raise RuntimeError("primary down")
        return {"px": 100.0}

    monkeypatch.setattr("gateway.live_price_session.connected_sources._price_from_connection", fetch)
    with pytest.raises(LivePriceUnavailable):
        await session.get("AAPL", force_refresh=True)
    assert calls == ["primary"]


@pytest.mark.asyncio
async def test_crosscheck_disagreement_blocks_qualification(monkeypatch):
    session = LivePriceSession()
    primary = {"id": "primary", "name": "PrimaryLive", "provider": "custom_json"}
    verifier = {"id": "verify", "name": "VerifierLive", "provider": "custom_json"}
    monkeypatch.setattr(
        "gateway.live_price_session.customer_runtime.enabled_connections",
        lambda category: [primary, verifier],
    )
    monkeypatch.setenv("LIVE_PRICE_REQUIRE_CROSSCHECK", "true")
    monkeypatch.setenv("LIVE_PRICE_MAX_CROSSCHECK_DIFF_PCT", "1.0")

    async def fetch(selected, ticker):
        return {"px": 100.0 if selected["id"] == "primary" else 103.0}

    monkeypatch.setattr("gateway.live_price_session.connected_sources._price_from_connection", fetch)
    with pytest.raises(LivePriceUnavailable, match="disagree"):
        await session.get("AAPL", force_refresh=True)


@pytest.mark.asyncio
async def test_crosscheck_required_blocks_when_only_one_provider_exists(monkeypatch):
    session = LivePriceSession()
    primary = {"id": "primary", "name": "PrimaryLive", "provider": "custom_json"}
    monkeypatch.setattr(
        "gateway.live_price_session.customer_runtime.enabled_connections",
        lambda category: [primary],
    )
    monkeypatch.setenv("LIVE_PRICE_REQUIRE_CROSSCHECK", "true")

    async def fetch(selected, ticker):
        return {"px": 100.0}

    monkeypatch.setattr("gateway.live_price_session.connected_sources._price_from_connection", fetch)
    with pytest.raises(LivePriceUnavailable, match="second independent"):
        await session.get("AAPL", force_refresh=True)


@pytest.mark.asyncio
async def test_strict_live_price_blocks_when_no_provider_is_configured(monkeypatch):
    session = LivePriceSession()
    monkeypatch.setattr(
        "gateway.live_price_session.customer_runtime.enabled_connections",
        lambda category: [],
    )
    with pytest.raises(LivePriceUnavailable):
        await session.get("AAPL")
