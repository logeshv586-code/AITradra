"""
ARBITRAGE AGENT — Claude Flow Architecture (100% OSS)
Scans for cross-exchange crypto arbitrage using CCXT public endpoints.
Exchanges: Binance, Bybit, OKX — all public, no API key required.

OBSERVE → Gather live prices from 3+ exchanges
THINK   → Identify spread anomalies
PLAN    → Rank opportunities by spread size
ACT     → Execute price fetches and compute spreads
REFLECT → Score confidence based on spread stability
"""

from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger
import asyncio

logger = get_logger(__name__)


class ArbitrageAgent(BaseAgent):
    """Detects cross-exchange crypto arbitrage opportunities via CCXT."""

    EXCHANGES = ["binance", "bybit", "okx"]
    MIN_SPREAD_PCT = 0.3  # Minimum 0.3% gap to signal

    def __init__(self, memory=None):
        super().__init__("ArbitrageAgent", memory)

    # ── OBSERVE ──────────────────────────────────────────────
    async def observe(self, context: AgentContext) -> AgentContext:
        ticker = context.ticker
        # Normalize crypto symbol
        if "USDT" not in ticker and "/" not in ticker:
            symbol = f"{ticker}/USDT"
        elif "USDT" in ticker and "/" not in ticker:
            symbol = ticker.replace("USDT", "/USDT")
        else:
            symbol = ticker

        context.observations["symbol"] = symbol
        context.observations["exchanges"] = self.EXCHANGES
        context.observations["is_crypto"] = any(
            x in ticker.upper() for x in ["BTC", "ETH", "SOL", "XRP", "DOGE", "BNB", "ADA", "DOT", "AVAX", "MATIC"]
        ) or "/" in ticker

        return context

    # ── THINK ────────────────────────────────────────────────
    async def think(self, context: AgentContext) -> AgentContext:
        if not context.observations.get("is_crypto"):
            self._add_thought(context, f"{context.ticker} is not a crypto pair — arbitrage scan skipped")
        else:
            self._add_thought(context, f"Will scan {len(self.EXCHANGES)} exchanges for {context.observations['symbol']}")
            self._add_thought(context, f"Minimum spread threshold: {self.MIN_SPREAD_PCT}%")
            self._add_thought(context, "Latency and withdrawal fees are NOT factored — this is signal-level only")
        return context

    # ── PLAN ─────────────────────────────────────────────────
    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "1. Fetch last price from each exchange via CCXT (public, no API key)",
            "2. Compute pairwise spread between all exchange combinations",
            "3. Flag opportunities where spread > MIN_SPREAD_PCT",
            "4. Sort by spread descending (best first)",
            "5. Return top opportunities with buy/sell exchange recommendation",
        ]
        return context

    # ── ACT ──────────────────────────────────────────────────
    async def act(self, context: AgentContext) -> AgentContext:
        if not context.observations.get("is_crypto"):
            context.result = {"signal": "SKIP", "reason": "Not a crypto pair", "opportunities": []}
            return context

        symbol = context.observations["symbol"]
        prices = {}
        opportunities = []

        try:
            import ccxt.async_support as ccxt

            async def fetch_price(ex_name):
                try:
                    exchange = getattr(ccxt, ex_name)()
                    ticker_data = await exchange.fetch_ticker(symbol)
                    await exchange.close()
                    return ex_name, ticker_data.get("last")
                except Exception as e:
                    logger.warning(f"CCXT {ex_name} fetch failed: {e}")
                    return ex_name, None

            results = await asyncio.gather(*(fetch_price(e) for e in self.EXCHANGES))

            for ex, price in results:
                if price is not None:
                    prices[ex] = price

            # Compute all pairwise spreads
            exchange_list = list(prices.keys())
            for i in range(len(exchange_list)):
                for j in range(i + 1, len(exchange_list)):
                    ex_a, ex_b = exchange_list[i], exchange_list[j]
                    pa, pb = prices[ex_a], prices[ex_b]
                    spread_pct = abs(pa - pb) / min(pa, pb) * 100

                    if spread_pct >= self.MIN_SPREAD_PCT:
                        buy_ex = ex_a if pa < pb else ex_b
                        sell_ex = ex_b if pa < pb else ex_a
                        opportunities.append({
                            "type": "cross_exchange",
                            "buy_exchange": buy_ex,
                            "buy_price": min(pa, pb),
                            "sell_exchange": sell_ex,
                            "sell_price": max(pa, pb),
                            "spread_pct": round(spread_pct, 4),
                        })

            opportunities.sort(key=lambda x: x["spread_pct"], reverse=True)
            context.actions_taken.append({"action": "ccxt_arb_scan", "exchanges_reached": len(prices)})

        except ImportError:
            context.errors.append("ccxt not installed — install via `pip install ccxt`")
        except Exception as e:
            context.errors.append(f"ArbitrageAgent ACT error: {e}")

        context.result = {
            "symbol": symbol,
            "prices_by_exchange": prices,
            "opportunities": opportunities[:10],
            "signal": "ARBITRAGE" if opportunities else "NO_OPPORTUNITY",
            "best_spread_pct": opportunities[0]["spread_pct"] if opportunities else 0.0,
        }
        return context

    # ── REFLECT ──────────────────────────────────────────────
    async def reflect(self, context: AgentContext) -> AgentContext:
        result = context.result or {}
        opps = result.get("opportunities", [])

        if opps:
            best = opps[0]["spread_pct"]
            context.reflection = f"Found {len(opps)} arbitrage opportunities. Best spread: {best:.2f}%"
            context.confidence = min(0.95, 0.5 + best / 10)
        elif not context.observations.get("is_crypto"):
            context.reflection = "Skipped — not a crypto pair"
            context.confidence = 0.0
        else:
            context.reflection = "No arbitrage opportunities above threshold"
            context.confidence = 0.1
        return context

    def _add_thought(self, context: AgentContext, thought: str):
        context.thoughts.append(f"[{self.name}] {thought}")
