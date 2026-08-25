import pytest

from core.primary_source_retry import (
    PrimarySourceUnavailable,
    bounded_backoff_seconds,
    primary_source_pair_ok,
    retry_primary_row,
)


def _row(collector: str, engine: str, diagnostic: str | None = None) -> dict:
    result = {
        "collector_source": collector,
        "data_engine_source": engine,
        "collector_close": 310.34,
        "data_engine_price": 310.34,
    }
    if diagnostic:
        result["primary_fetch_diagnostic"] = diagnostic
    return result


def test_primary_source_pair_requires_both_authoritative_sources():
    assert primary_source_pair_ok(_row("yfinance", "yfinance"), "yfinance") is True
    assert primary_source_pair_ok(_row("stooq", "yfinance"), "yfinance") is False
    assert primary_source_pair_ok(_row("yfinance", "yahoo_scrape_html"), "yfinance") is False


def test_bounded_backoff_is_exponential_and_capped():
    assert bounded_backoff_seconds(1, base_seconds=5, max_seconds=20) == 5
    assert bounded_backoff_seconds(2, base_seconds=5, max_seconds=20) == 10
    assert bounded_backoff_seconds(3, base_seconds=5, max_seconds=20) == 20
    assert bounded_backoff_seconds(4, base_seconds=5, max_seconds=20) == 20


@pytest.mark.asyncio
async def test_retry_recovers_without_accepting_fallback():
    rows = [
        _row("yahoo_scrape_html", "not_checked", "YFRateLimitError: Too Many Requests"),
        _row("yfinance", "yfinance"),
    ]
    sleep_calls: list[float] = []

    async def fetch_row():
        return rows.pop(0)

    async def fake_sleep(delay: float):
        sleep_calls.append(delay)

    row, telemetry = await retry_primary_row(
        fetch_row,
        required_source="yfinance",
        max_attempts=3,
        base_delay_seconds=0.25,
        max_delay_seconds=1,
        sleep=fake_sleep,
    )

    assert row["collector_source"] == "yfinance"
    assert telemetry["status"] == "RECOVERED"
    assert telemetry["attempt_count"] == 2
    assert telemetry["fallback_accepted"] is False
    assert telemetry["attempts"][0]["accepted"] is False
    assert "YFRateLimitError" in telemetry["attempts"][0]["diagnostic"]
    assert sleep_calls == [0.25]


@pytest.mark.asyncio
async def test_retry_records_exception_then_recovers():
    calls = 0

    async def fetch_row():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary provider failure")
        return _row("yfinance", "yfinance")

    async def fake_sleep(_delay: float):
        return None

    _, telemetry = await retry_primary_row(
        fetch_row,
        required_source="yfinance",
        max_attempts=2,
        base_delay_seconds=0,
        sleep=fake_sleep,
    )

    first = telemetry["attempts"][0]
    assert first["failure_kind"] == "primary_source_fetch_error"
    assert first["error_type"] == "RuntimeError"
    assert "temporary provider failure" in first["error_message"]


@pytest.mark.asyncio
async def test_retry_exhaustion_fails_closed_with_full_telemetry():
    async def fetch_row():
        return _row("stooq", "not_checked")

    async def fake_sleep(_delay: float):
        return None

    with pytest.raises(PrimarySourceUnavailable) as exc_info:
        await retry_primary_row(
            fetch_row,
            required_source="yfinance",
            max_attempts=3,
            base_delay_seconds=0,
            sleep=fake_sleep,
        )

    telemetry = exc_info.value.telemetry
    assert telemetry["status"] == "FAIL"
    assert telemetry["attempt_count"] == 3
    assert telemetry["fallback_accepted"] is False
    assert all(item["accepted"] is False for item in telemetry["attempts"])
