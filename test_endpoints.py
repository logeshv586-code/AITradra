"""AXIOM V4 Mythic Architecture — Endpoint Verification Script.

Tests ALL API endpoints to validate the full pipeline.
Run: python test_endpoints.py  (server must be running on port 8000)
"""

import asyncio
import httpx
import json
import sys

BASE = "http://localhost:8000"

TESTS = [
    ("GET",  "/health",                     None,   "Health check"),
    ("GET",  "/api/market/watchlist",        None,   "Watchlist data"),
    ("GET",  "/api/market/indices",          None,   "Market indices"),
    ("GET",  "/api/agents/status",           None,   "Agent status (V3+V4)"),
    ("GET",  "/api/pipeline/status",         None,   "Mythic pipeline health"),
    ("POST", "/api/chat",                    {"message": "What is AAPL trading at?", "ticker": "AAPL"}, "Chat API"),
    ("GET",  "/api/stock/AAPL/detail",       None,   "Stock detail"),
    ("GET",  "/api/stock/AAPL/news",         None,   "Stock news"),
    ("GET",  "/api/knowledge/status",        None,   "Knowledge store status"),
    ("GET",  "/api/db/status",              None,   "DB portability status"),
    ("POST", "/api/db/snapshot",            None,   "DB snapshot"),
]


async def run_tests():
    passed = 0
    failed = 0
    errors = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        for method, path, body, desc in TESTS:
            url = f"{BASE}{path}"
            try:
                if method == "GET":
                    r = await client.get(url)
                else:
                    r = await client.post(url, json=body or {})

                if r.status_code < 400:
                    data = r.json()
                    print(f"  ✅ [{r.status_code}] {desc:30s} {path}")
                    
                    # Specific validations
                    if path == "/health":
                        assert data.get("version") == "4.0.0", f"Expected version 4.0.0, got {data.get('version')}"
                        assert data.get("mythic_agents") == 5, "Expected 5 mythic agents"
                    
                    if path == "/api/agents/status":
                        agents = data.get("agents", [])
                        mythic = [a for a in agents if a.get("type") == "v4_mythic"]
                        assert len(mythic) == 5, f"Expected 5 mythic agents, got {len(mythic)}"
                        print(f"         → {len(agents)} total agents, {len(mythic)} mythic-tier")
                    
                    if path == "/api/pipeline/status":
                        assert data.get("pipeline") == "mythic_v4"
                        assert data.get("status") == "operational"
                        print(f"         → Pipeline: {data.get('status')}, Memory: {data.get('memory', {})}")
                    
                    if path == "/api/chat":
                        response_text = data.get("response", "")
                        print(f"         → Response length: {len(response_text)} chars")
                    
                    if path == "/api/db/status":
                        tables = data.get("tables", {})
                        print(f"         → OHLCV: {tables.get('daily_ohlcv', 0)}, News: {tables.get('news_articles', 0)}")
                    
                    passed += 1
                else:
                    print(f"  ❌ [{r.status_code}] {desc:30s} {path}")
                    errors.append(f"{path}: HTTP {r.status_code} - {r.text[:200]}")
                    failed += 1

            except httpx.ConnectError:
                print(f"  ⚠️  [CONN] {desc:30s} Server not running!")
                errors.append(f"{path}: Connection refused")
                failed += 1
            except AssertionError as e:
                print(f"  ❌ [ASSERT] {desc:30s} {e}")
                errors.append(f"{path}: Assertion failed - {e}")
                failed += 1
            except Exception as e:
                print(f"  ❌ [ERR]  {desc:30s} {e}")
                errors.append(f"{path}: {e}")
                failed += 1

    # Summary
    total = passed + failed
    print(f"\n{'='*60}")
    print(f"  AXIOM V4 Mythic Endpoint Tests")
    print(f"  Passed: {passed}/{total}  Failed: {failed}/{total}")
    print(f"{'='*60}")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  - {e}")

    return failed == 0


if __name__ == "__main__":
    print("=" * 60)
    print("  AXIOM V4 MYTHIC — Endpoint Verification")
    print("  Server: http://localhost:8000")
    print("=" * 60 + "\n")

    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
