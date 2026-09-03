"""Strategy Generator Agent — Convert natural language to trading code.

Generated strategies are research artifacts only. Their Vibe backtest output is
parsed into measured metrics, and a backtest is marked successful only when
meaningful statistics are actually present. Generated code never bypasses
AITradra's SystematicResearch/Backtrader/risk/precision execution gates.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

from agents.base_agent import BaseAgent, AgentContext
from core.vibe_gateway import vibe_gateway
from core.logger import get_logger

logger = get_logger(__name__)


class StrategyLanguage(Enum):
    PINE = "pine"
    MQL5 = "mql5"
    PYTHON = "python"
    QUANTCONNECT = "quantconnect"


class StrategyMarket(Enum):
    CRYPTO = "crypto"
    STOCKS = "stocks"
    FOREX = "forex"
    FUTURES = "futures"
    OPTIONS = "options"


@dataclass
class StrategySpec:
    description: str
    language: StrategyLanguage = StrategyLanguage.PINE
    market: StrategyMarket = StrategyMarket.CRYPTO
    timeframe: str = "1h"
    risk_profile: str = "moderate"
    include_comments: bool = True
    include_backtest: bool = True


@dataclass
class GeneratedStrategy:
    success: bool
    language: str
    market: str
    code: str = ""
    description: str = ""
    indicators_used: List[str] = field(default_factory=list)
    entry_conditions: List[str] = field(default_factory=list)
    exit_conditions: List[str] = field(default_factory=list)
    risk_parameters: Dict[str, Any] = field(default_factory=dict)
    backtest_summary: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0


@dataclass
class BacktestResult:
    success: bool
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    avg_trade: float = 0.0
    total_return: float = 0.0
    equity_curve: List[float] = field(default_factory=list)
    trades: List[Dict[str, Any]] = field(default_factory=list)
    parsed_metrics: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    execution_authority: bool = False


class StrategyGeneratorAgent(BaseAgent):
    """Generate strategy code and parse external backtests without trusting them blindly."""

    def __init__(self, memory=None):
        super().__init__(name="StrategyGenerator", memory=memory)
        self.vibe = vibe_gateway
        self._available = self.vibe.is_available

    @property
    def is_available(self) -> bool:
        return self._available

    async def observe(self, context: AgentContext) -> AgentContext:
        context.observations["strategy_generation_available"] = self._available
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, f"Preparing research-only strategy generation in {context.metadata.get('language', 'pine')}")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan.extend(
            [
                "Translate the strategy brief into code",
                "Run the requested external research backtest when asked",
                "Parse measurable metrics instead of trusting a success string",
                "Require AITradra native validation before any execution eligibility",
            ]
        )
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        result = await self.generate(
            description=context.task,
            language=context.metadata.get("language", "pine"),
            market=context.metadata.get("market", "crypto"),
            context=context,
        )
        context.result = {
            "success": result.success,
            "language": result.language,
            "market": result.market,
            "code": result.code,
            "errors": result.errors,
            "execution_authority": False,
        }
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        context.confidence = 0.5 if context.result.get("success") else 0.0
        context.reflection = (
            "Strategy generation succeeded as a research artifact; native validation is still required."
            if context.result.get("success")
            else "Strategy generation failed."
        )
        return context

    async def generate(
        self,
        description: str,
        language: str = "pine",
        market: str = "crypto",
        context: Optional[AgentContext] = None,
    ) -> GeneratedStrategy:
        import time

        start_time = time.time()
        if not self._available:
            return GeneratedStrategy(
                success=False,
                language=language,
                market=market,
                errors=["Vibe Trading AI not available"],
            )

        self._add_thought(
            context or AgentContext(task=description),
            f"Generating {language} research strategy: {description[:50]}...",
        )
        try:
            response = await asyncio.wait_for(
                self.vibe.generate_strategy(
                    description=description, language=language, market=market
                ),
                timeout=180,
            )
            execution_time = (time.time() - start_time) * 1000
            if response.get("error"):
                return GeneratedStrategy(
                    success=False,
                    language=language,
                    market=market,
                    execution_time_ms=execution_time,
                    errors=[str(response["error"])],
                )
            output = str(response.get("output", "") or "")
            if not output.strip():
                return GeneratedStrategy(
                    success=False,
                    language=language,
                    market=market,
                    execution_time_ms=execution_time,
                    errors=["Strategy generator returned no code"],
                )
            return GeneratedStrategy(
                success=True,
                language=language,
                market=market,
                code=output,
                description=description,
                execution_time_ms=execution_time,
            )
        except asyncio.TimeoutError:
            return GeneratedStrategy(
                success=False,
                language=language,
                market=market,
                errors=["Strategy generation timed out after 180s"],
            )
        except Exception as exc:
            logger.error("Strategy generation failed: %s", exc)
            return GeneratedStrategy(
                success=False, language=language, market=market, errors=[str(exc)]
            )

    async def generate_and_backtest(
        self,
        description: str,
        ticker: str,
        language: str = "python",
        market: str = "crypto",
        timeframe: str = "1h",
        engine: str = "composite",
    ) -> Dict[str, Any]:
        strategy = await self.generate(description, language, market)
        if not strategy.success:
            return {
                "strategy": strategy,
                "backtest": None,
                "error": strategy.errors,
                "native_validation_required": True,
                "execution_authority": False,
            }
        backtest = await self.backtest(strategy.code, ticker, timeframe, engine)
        return {
            "strategy": strategy,
            "backtest": backtest,
            "native_validation_required": True,
            "required_next_gate": "SystematicResearchEngine -> BacktestAgent -> Risk -> PrecisionGate",
            "execution_authority": False,
        }

    async def backtest(
        self,
        strategy_code: str,
        ticker: str,
        timeframe: str = "1h",
        engine: str = "composite",
    ) -> BacktestResult:
        if not self._available:
            return BacktestResult(success=False, errors=["Vibe Trading AI not available"])
        try:
            response = await asyncio.wait_for(
                self.vibe.run_backtest(
                    strategy_code=strategy_code,
                    ticker=ticker,
                    timeframe=timeframe,
                    engine=engine,
                ),
                timeout=600,
            )
            if response.get("error"):
                return BacktestResult(success=False, errors=[str(response["error"])])
            return self._parse_backtest(str(response.get("output", "") or ""))
        except asyncio.TimeoutError:
            return BacktestResult(success=False, errors=["Backtest timed out after 600s"])
        except Exception as exc:
            logger.error("Backtest failed: %s", exc)
            return BacktestResult(success=False, errors=[str(exc)])

    @staticmethod
    def _coerce_number(value: Any, default: float = 0.0) -> float:
        if isinstance(value, str):
            value = value.replace("%", "").replace(",", "").strip()
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _find_metric_dict(cls, payload: Any) -> dict[str, Any] | None:
        aliases = {
            "total_trades", "trades", "num_trades", "trade_count",
            "win_rate", "profit_factor", "sharpe", "sharpe_ratio",
            "max_drawdown", "max_drawdown_pct", "total_return", "return_pct",
        }
        if isinstance(payload, dict):
            lowered = {str(k).lower() for k in payload}
            if lowered & aliases:
                return payload
            for value in payload.values():
                found = cls._find_metric_dict(value)
                if found:
                    return found
        elif isinstance(payload, list):
            for value in payload:
                found = cls._find_metric_dict(value)
                if found:
                    return found
        return None

    @staticmethod
    def _json_candidates(output: str) -> list[Any]:
        candidates: list[Any] = []
        try:
            candidates.append(json.loads(output))
        except Exception:
            pass
        for match in re.finditer(r"\{[\s\S]*?\}", output):
            try:
                candidates.append(json.loads(match.group(0)))
            except Exception:
                continue
        return candidates

    @classmethod
    def _regex_metric(cls, output: str, names: list[str]) -> float | None:
        joined = "|".join(re.escape(name) for name in names)
        match = re.search(
            rf"(?:{joined})\s*[:=]\s*([+-]?[0-9][0-9,]*(?:\.[0-9]+)?)\s*(%)?",
            output,
            flags=re.IGNORECASE,
        )
        if not match:
            return None
        return cls._coerce_number(match.group(1))

    @classmethod
    def _parse_backtest(cls, output: str) -> BacktestResult:
        """Parse structured or textual Vibe output into non-fabricated metrics."""
        metric_payload: dict[str, Any] | None = None
        root_payload: Any = None
        for candidate in cls._json_candidates(output):
            found = cls._find_metric_dict(candidate)
            if found:
                metric_payload = found
                root_payload = candidate
                break

        aliases: dict[str, list[str]] = {
            "total_trades": ["total_trades", "trades", "num_trades", "trade_count"],
            "winning_trades": ["winning_trades", "wins", "won"],
            "losing_trades": ["losing_trades", "losses", "lost"],
            "win_rate": ["win_rate", "winrate"],
            "profit_factor": ["profit_factor", "profitfactor"],
            "sharpe_ratio": ["sharpe_ratio", "sharpe"],
            "max_drawdown": ["max_drawdown", "max_drawdown_pct", "drawdown"],
            "avg_trade": ["avg_trade", "average_trade", "avg_trade_return"],
            "total_return": ["total_return", "total_return_pct", "return_pct", "net_return"],
        }

        def from_dict(keys: list[str]) -> Any:
            if not metric_payload:
                return None
            lowered = {str(key).lower(): value for key, value in metric_payload.items()}
            for key in keys:
                if key in lowered:
                    return lowered[key]
            return None

        values: dict[str, float] = {}
        parsed: list[str] = []
        for metric, names in aliases.items():
            raw = from_dict(names)
            if raw is None:
                raw = cls._regex_metric(output, names)
            if raw is None:
                continue
            values[metric] = cls._coerce_number(raw)
            parsed.append(metric)

        win_rate = values.get("win_rate", 0.0)
        if win_rate > 1.0:
            win_rate /= 100.0
        max_drawdown = abs(values.get("max_drawdown", 0.0))
        total_return = values.get("total_return", 0.0)

        trades: list[dict[str, Any]] = []
        equity: list[float] = []
        if isinstance(root_payload, dict):
            candidate_trades = root_payload.get("trades")
            candidate_equity = root_payload.get("equity_curve") or root_payload.get("equity")
            if isinstance(candidate_trades, list):
                trades = [row for row in candidate_trades if isinstance(row, dict)]
            if isinstance(candidate_equity, list):
                equity = [cls._coerce_number(v) for v in candidate_equity]

        total_trades = int(max(0, round(values.get("total_trades", len(trades)))))
        meaningful_metrics = {
            name for name in parsed if name in {"win_rate", "profit_factor", "sharpe_ratio", "max_drawdown", "total_return"}
        }
        success = total_trades > 0 and len(meaningful_metrics) >= 2
        errors: list[str] = []
        if not success:
            errors.append(
                "Vibe backtest output did not contain enough measurable performance evidence; native validation is required"
            )

        return BacktestResult(
            success=success,
            total_trades=total_trades,
            winning_trades=int(max(0, round(values.get("winning_trades", 0.0)))),
            losing_trades=int(max(0, round(values.get("losing_trades", 0.0)))),
            win_rate=round(max(0.0, min(win_rate, 1.0)), 6),
            profit_factor=round(max(0.0, values.get("profit_factor", 0.0)), 6),
            sharpe_ratio=round(values.get("sharpe_ratio", 0.0), 6),
            max_drawdown=round(max_drawdown, 6),
            avg_trade=round(values.get("avg_trade", 0.0), 6),
            total_return=round(total_return, 6),
            equity_curve=equity,
            trades=trades,
            parsed_metrics=parsed,
            errors=errors,
            execution_authority=False,
        )

    async def convert_code(
        self, source_code: str, from_language: str, to_language: str
    ) -> GeneratedStrategy:
        description = f"Convert from {from_language} to {to_language}: {source_code[:200]}"
        return await self.generate(description, to_language, "crypto")

    def get_supported_languages(self) -> List[str]:
        return [e.value for e in StrategyLanguage]

    def get_supported_markets(self) -> List[str]:
        return [e.value for e in StrategyMarket]


strategy_generator_agent = StrategyGeneratorAgent()
