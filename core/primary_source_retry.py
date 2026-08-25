"""Fail-closed retry policy for authoritative market-data source availability.

A fallback provider may be observed for diagnostics, but it is never accepted as
an authoritative substitute.  The caller can retry the same required primary
source with bounded backoff and preserve every failed attempt as evidence.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable


class PrimarySourceUnavailable(AssertionError):
    """Raised after the authoritative source exhausts its retry budget."""

    def __init__(self, message: str, telemetry: dict[str, Any]):
        super().__init__(message)
        self.telemetry = telemetry


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def bounded_backoff_seconds(
    attempt: int,
    *,
    base_seconds: float = 5.0,
    max_seconds: float = 20.0,
) -> float:
    """Return deterministic exponential backoff bounded by ``max_seconds``."""
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    base = max(float(base_seconds), 0.0)
    cap = max(float(max_seconds), base)
    return min(base * (2 ** (attempt - 1)), cap)


def primary_source_pair_ok(row: dict[str, Any], required_source: str) -> bool:
    """Both collector and DataEngine evidence must resolve to the primary."""
    required = str(required_source).strip().lower()
    collector = str(row.get("collector_source") or "").strip().lower()
    engine = str(row.get("data_engine_source") or "").strip().lower()
    return collector == required and engine == required


def _row_attempt_record(
    row: dict[str, Any],
    *,
    attempt: int,
    required_source: str,
) -> dict[str, Any]:
    accepted = primary_source_pair_ok(row, required_source)
    record: dict[str, Any] = {
        "attempt": attempt,
        "checked_at": utc_now(),
        "required_source": required_source,
        "collector_source": row.get("collector_source"),
        "data_engine_source": row.get("data_engine_source"),
        "accepted": accepted,
    }
    diagnostic = row.get("primary_fetch_diagnostic")
    if diagnostic:
        record["diagnostic"] = str(diagnostic)[-2000:]
    if not accepted:
        record["failure_kind"] = "primary_source_substitution_blocked"
    return record


async def retry_primary_row(
    fetch_row: Callable[[], Awaitable[dict[str, Any]]],
    *,
    required_source: str,
    max_attempts: int = 4,
    base_delay_seconds: float = 5.0,
    max_delay_seconds: float = 20.0,
    before_retry: Callable[[int, dict[str, Any]], Awaitable[None]] | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Retry until both source observations are authoritative or fail closed.

    ``fetch_row`` may return evidence from a fallback source.  Such evidence is
    recorded but never accepted.  Exceptions are also recorded with type and
    message.  When retries are exhausted, ``PrimarySourceUnavailable`` carries
    the complete attempt telemetry for artifact publication.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    attempts: list[dict[str, Any]] = []
    started_at = utc_now()

    for attempt in range(1, max_attempts + 1):
        try:
            row = await fetch_row()
            record = _row_attempt_record(
                row,
                attempt=attempt,
                required_source=required_source,
            )
        except Exception as exc:  # evidence is preserved, then retry remains fail-closed
            row = {}
            record = {
                "attempt": attempt,
                "checked_at": utc_now(),
                "required_source": required_source,
                "collector_source": None,
                "data_engine_source": None,
                "accepted": False,
                "failure_kind": "primary_source_fetch_error",
                "error_type": type(exc).__name__,
                "error_message": str(exc)[-2000:],
            }

        attempts.append(record)
        if record["accepted"]:
            return row, {
                "status": "PASS" if attempt == 1 else "RECOVERED",
                "required_source": required_source,
                "started_at": started_at,
                "finished_at": utc_now(),
                "attempt_count": attempt,
                "recovered_after_transient_failure": attempt > 1,
                "fallback_accepted": False,
                "attempts": attempts,
            }

        if attempt < max_attempts:
            delay = bounded_backoff_seconds(
                attempt,
                base_seconds=base_delay_seconds,
                max_seconds=max_delay_seconds,
            )
            record["retry_delay_seconds"] = delay
            if before_retry is not None:
                await before_retry(attempt, record)
            await sleep(delay)

    telemetry = {
        "status": "FAIL",
        "required_source": required_source,
        "started_at": started_at,
        "finished_at": utc_now(),
        "attempt_count": len(attempts),
        "recovered_after_transient_failure": False,
        "fallback_accepted": False,
        "attempts": attempts,
    }
    raise PrimarySourceUnavailable(
        f"Authoritative source {required_source!r} unavailable after {max_attempts} attempts; "
        "fallback substitution remained blocked",
        telemetry,
    )
