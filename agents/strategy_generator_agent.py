"""Strategy Generator Agent — Convert natural language to trading code.

Generates Pine Script, MQL5, Python, or QuantConnect code from strategy
descriptions using Vibe Trading AI's generation engine.
"""

import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

from agents.base_agent import BaseAgent, AgentContext
from core.vibe_gateway import vibe_gateway
from core.logger import get_logger

logger = get_logger(__name__)


class StrategyLanguage(Enum):
    """Target code language for strategy generation."""

    PINE = "pine"
    MQL5 = "mql5"
    PYTHON = "python"
    QUANTCONNECT = "quantconnect"


class StrategyMarket(Enum):
    """Target market for strategy."""

    CRYPTO = "crypto"
    STOCKS = "stocks"
    FOREX = "forex"
    FUTURES = "futures"
    OPTIONS = "options"


@dataclass
class StrategySpec:
    """Specification for strategy generation."""

    description: str
    language: StrategyLanguage = StrategyLanguage.PINE
    market: StrategyMarket = StrategyMarket.CRYPTO
    timeframe: str = "1h"
    risk_profile: str = "moderate"
    include_comments: bool = True
    include_backtest: bool = True


@dataclass
class GeneratedStrategy:
    """Generated trading strategy code."""

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
    """Backtest results for generated strategy."""

    success: bool
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    avg_trade: float = 0.0
    equity_curve: List[float] = field(default_factory=list)
    trades: List[Dict[str, Any]] = field(default_factory=list)


class StrategyGeneratorAgent(BaseAgent):
    """Agent for generating trading strategies from natural language.

    Converts strategy descriptions into executable code in various
    trading platforms and languages.
    """

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
        self._add_thought(
            context,
            f"Preparing strategy generation in {context.metadata.get('language', 'pine')}",
        )
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan.append("Translate the strategy brief into executable code")
        context.plan.append("Return the generated strategy and metadata")
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
        }
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        context.confidence = 1.0 if context.result.get("success") else 0.0
        context.reflection = (
            f"Strategy generation {'succeeded' if context.result.get('success') else 'failed'}."
        )
        return context

    async def generate(
        self,
        description: str,
        language: str = "pine",
        market: str = "crypto",
        context: Optional[AgentContext] = None,
    ) -> GeneratedStrategy:
        """Generate trading strategy code from description.

        Args:
            description: Natural language strategy description
            language: Target language (pine, mql5, python, quantconnect)
            market: Target market type
            context: Optional agent context

        Returns:
            GeneratedStrategy with code and metadata
        """
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
            f"Generating {language} strategy: {description[:50]}...",
        )

        try:
            response = await asyncio.wait_for(
                self.vibe.generate_strategy(
                    strategy描述=description, language=language, market=market
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
                    errors=[response["error"]],
                )

            output = response.get("output", "")

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
        except Exception as e:
            logger.error(f"Strategy generation failed: {e}")
            return GeneratedStrategy(
                success=False, language=language, market=market, errors=[str(e)]
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
        """Generate strategy and run backtest in one operation.

        Args:
            description: Strategy description
            ticker: Asset to backtest
            language: Code language
            market: Market type
            timeframe: Data timeframe
            engine: Backtest engine

        Returns:
            Dict with generated strategy and backtest results
        """
        strategy = await self.generate(description, language, market)

        if not strategy.success:
            return {"strategy": strategy, "backtest": None, "error": strategy.errors}

        backtest = await self.backtest(strategy.code, ticker, timeframe, engine)

        return {"strategy": strategy, "backtest": backtest}

    async def backtest(
        self,
        strategy_code: str,
        ticker: str,
        timeframe: str = "1h",
        engine: str = "composite",
    ) -> BacktestResult:
        """Run backtest on strategy code.

        Args:
            strategy_code: Strategy script content
            ticker: Asset to backtest
            timeframe: Data timeframe
            engine: Backtest engine

        Returns:
            BacktestResult with metrics and trades
        """
        if not self._available:
            return BacktestResult(
                success=False, total_trades=0, errors=["Vibe Trading AI not available"]
            )

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
                return BacktestResult(success=False, errors=[response["error"]])

            output = response.get("output", "")

            return self._parse_backtest(output)

        except asyncio.TimeoutError:
            return BacktestResult(
                success=False, total_trades=0, errors=["Backtest timed out after 600s"]
            )
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            return BacktestResult(success=False, total_trades=0, errors=[str(e)])

    def _parse_backtest(self, output: str) -> BacktestResult:
        """Parse backtest output into structured result."""
        return BacktestResult(
            success=True,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            profit_factor=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            avg_trade=0.0,
            equity_curve=[],
            trades=[],
        )

    async def convert_code(
        self, source_code: str, from_language: str, to_language: str
    ) -> GeneratedStrategy:
        """Convert strategy code between languages.

        Args:
            source_code: Original strategy code
            from_language: Source language
            to_language: Target language

        Returns:
            Converted strategy code
        """
        description = (
            f"Convert from {from_language} to {to_language}: {source_code[:200]}"
        )
        return await self.generate(description, to_language, "crypto")

    def get_supported_languages(self) -> List[str]:
        """List supported output languages."""
        return [e.value for e in StrategyLanguage]

    def get_supported_markets(self) -> List[str]:
        """List supported markets."""
        return [e.value for e in StrategyMarket]


strategy_generator_agent = StrategyGeneratorAgent()
