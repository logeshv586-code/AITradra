"""Export immutable empirical precision evidence for audit/review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from self_improvement.precision_store import precision_store


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export live-gate-eligible prediction evidence as JSON."
    )
    parser.add_argument("--ticker", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument(
        "--out",
        default="precision-evidence-audit.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    rows = precision_store.export_evidence(
        ticker=args.ticker,
        model=args.model,
        limit=args.limit,
    )
    payload = {
        "schema": "aitradra.precision_evidence.v2",
        "eligible_rows": len(rows),
        "ticker": args.ticker,
        "model": args.model,
        "rows": rows,
        "note": (
            "Only immutable live-gate-eligible evidence is exported. "
            "Legacy/research accuracy is intentionally excluded."
        ),
    }
    out = Path(args.out)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
