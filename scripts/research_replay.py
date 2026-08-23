"""Replay AITradra research at a historical point in time without trading.

Example:
    python scripts/research_replay.py AAPL --as-of 2026-07-15T20:00:00+00:00

The command deliberately has no broker/execution integration.  It is intended
for leakage checks, research audits and walk-forward evidence collection.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from agents.research_council import get_research_council


async def _run(args) -> dict:
    decision = await get_research_council().analyze(
        args.ticker,
        as_of=args.as_of,
        use_llm_debate=not args.no_llm,
        persist=not args.no_persist,
    )
    return decision.to_dict()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replay point-in-time AITradra research with future evidence excluded."
    )
    parser.add_argument("ticker", help="Ticker such as AAPL, RELIANCE.NS or BTC-USD")
    parser.add_argument(
        "--as-of",
        required=True,
        help="ISO-8601 research cutoff. Evidence newer than this timestamp is excluded.",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Use only deterministic weighted evidence; do not run the adversarial LLM debate.",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Do not write the replay decision back to the research/debate ledger.",
    )
    parser.add_argument("--out", default="", help="Optional JSON output path")
    args = parser.parse_args()

    payload = asyncio.run(_run(args))
    rendered = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
