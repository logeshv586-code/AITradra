"""Quantic Analysis Agent — Advanced quantitative analysis powered by Vibe Trading AI.

Provides SMC (Smart Money Concepts), Monte Carlo simulations, and bootstrap
validation for trading strategies and market analysis.
"""

import asyncio
import re
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from agents.base_agent import BaseAgent, AgentContext
from core.vibe_gateway import vibe_gateway
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class QuanticConfig:
    """Configuration for quantic analysis."""

    ticker: str
    analysis_type: str = "full"
    timeframe: str = "1h"
    confidence_level: float = 0.95
    mc_simulations: int = 10000
    bootstrap_samples: int = 5000


@dataclass
class SMCAnalysis:
    """Smart Money Concepts analysis results."""

    institutional_order_blocks: List[Dict[str, Any]] = field(default_factory=list)
    fair_value_gaps: List[Dict[str, Any]] = field(default_factory=list)
    liquidity_pools: List[Dict[str, Any]] = field(default_factory=list)
    order_flow_imbalance: float = 0.0
    smart_money_signal: str = "NEUTRAL"
    confidence: float = 0.0


@dataclass
class MonteCarloResult:
    """Monte Carlo simulation results."""

    expected_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    percentile_5: float = 0.0
    percentile_95: float = 0.0
    distribution: List[float] = field(default_factory=list)


@dataclass
class BootstrapResult:
    """Bootstrap validation results."""

    mean_estimate: float = 0.0
    std_error: float = 0.0
    confidence_interval: tuple = (0.0, 0.0)
    p_value: float = 0.0
    is_significant: bool = False


@dataclass
class QuanticResult:
    """Complete quantic analysis result."""

    success: bool
    ticker: str
    timeframe: str
    smc: Optional[SMCAnalysis] = None
    monte_carlo: Optional[MonteCarloResult] = None
    bootstrap: Optional[BootstrapResult] = None
    synthesis: str = ""
    errors: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0

    @property
    def smart_money_score(self) -> float:
        """Compute a normalized smart money score (0-100)."""
        if not self.smc:
            return 50.0

        score = 50.0

        signal = self.smc.smart_money_signal.upper()
        if signal == "BULLISH":
            score += 20
        elif signal == "BEARISH":
            score -= 20

        score += (self.smc.confidence - 0.5) * 40

        if self.smc.order_flow_imbalance > 0.5:
            score += 10
        elif self.smc.order_flow_imbalance < -0.5:
            score -= 10

        if self.smc.institutional_order_blocks:
            score += len(self.smc.institutional_order_blocks) * 3

        return max(0, min(100, score))


class QuanticAnalysisAgent(BaseAgent):
    """Agent for advanced quantitative analysis.

    Provides:
    - Smart Money Concepts (SMC) analysis
    - Monte Carlo simulation for risk/reward
    - Bootstrap validation for statistical significance
    """

    def __init__(self, memory=None):
        super().__init__(name="QuanticAnalysis", memory=memory)
        self.vibe = vibe_gateway
        self._available = self.vibe.is_available

    @property
    def is_available(self) -> bool:
        return self._available

    async def observe(self, context: AgentContext) -> AgentContext:
        context.observations["quantic_available"] = self._available
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        target = context.ticker or context.metadata.get("ticker", "")
        self._add_thought(context, f"Preparing quantic analysis for {target}")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan.append("Run SMC, Monte Carlo, and bootstrap validation")
        context.plan.append("Parse structured quantic outputs")
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        ticker = context.ticker or context.metadata.get("ticker", "")
        result = await self.execute(
            ticker=ticker,
            analysis_type=context.metadata.get("analysis_type", "full"),
            timeframe=context.metadata.get("timeframe", "1h"),
            context=context,
        )
        context.result = {
            "success": result.success,
            "ticker": result.ticker,
            "timeframe": result.timeframe,
            "smart_money_score": result.smart_money_score,
            "synthesis": result.synthesis,
            "errors": result.errors,
        }
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        context.confidence = _safe_confidence_from_result(context.result)
        context.reflection = (
            f"Quantic analysis {'succeeded' if context.result.get('success') else 'failed'}."
        )
        return context

    async def execute(
        self,
        ticker: str,
        analysis_type: str = "full",
        timeframe: str = "1h",
        context: Optional[AgentContext] = None,
    ) -> QuanticResult:
        """Execute full quantic analysis on an asset.

        Args:
            ticker: Asset symbol (e.g., "BTC", "AAPL", "NIFTY")
            analysis_type: Type of analysis (smc, monte_carlo, bootstrap, full)
            timeframe: Data timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            context: Optional agent context

        Returns:
            QuanticResult with all analysis components
        """
        import time

        start_time = time.time()

        if not self._available:
            return QuanticResult(
                success=False,
                ticker=ticker,
                timeframe=timeframe,
                errors=["Vibe Trading AI not available"],
            )

        self._add_thought(
            context or AgentContext(task=f"Analyze {ticker}"),
            f"Running {analysis_type} analysis on {ticker} ({timeframe})",
        )

        try:
            response = await asyncio.wait_for(
                self.vibe.run_quantic_analysis(
                    ticker=ticker, analysis_type=analysis_type, timeframe=timeframe
                ),
                timeout=300,
            )

            execution_time = (time.time() - start_time) * 1000

            if response.get("error"):
                return QuanticResult(
                    success=False,
                    ticker=ticker,
                    timeframe=timeframe,
                    execution_time_ms=execution_time,
                    errors=[response["error"]],
                )

            output = response.get("output", "")

            smc = self._parse_smc(output) if analysis_type in ("smc", "full") else None
            mc = (
                self._parse_monte_carlo(output)
                if analysis_type in ("monte_carlo", "full")
                else None
            )
            bootstrap = (
                self._parse_bootstrap(output)
                if analysis_type in ("bootstrap", "full")
                else None
            )

            return QuanticResult(
                success=True,
                ticker=ticker,
                timeframe=timeframe,
                smc=smc,
                monte_carlo=mc,
                bootstrap=bootstrap,
                synthesis=output,
                execution_time_ms=execution_time,
            )

        except asyncio.TimeoutError:
            return QuanticResult(
                success=False,
                ticker=ticker,
                timeframe=timeframe,
                errors=["Analysis timed out after 300s"],
            )
        except Exception as e:
            logger.error(f"Quantic analysis failed: {e}")
            return QuanticResult(
                success=False, ticker=ticker, timeframe=timeframe, errors=[str(e)]
            )

    async def run_smc_analysis(self, ticker: str, timeframe: str = "1h") -> SMCAnalysis:
        """Run only Smart Money Concepts analysis.

        Identifies:
        - Institutional order blocks
        - Fair value gaps (FVG)
        - Liquidity pools/sweeps
        - Order flow imbalance
        """
        result = await self.execute(ticker, "smc", timeframe)
        return result.smc or SMCAnalysis()

    async def run_monte_carlo(
        self, ticker: str, timeframe: str = "1h", simulations: int = 10000
    ) -> MonteCarloResult:
        """Run Monte Carlo simulation for risk assessment.

        Computes:
        - Expected return distribution
        - Volatility estimates
        - Sharpe ratio distribution
        - Max drawdown distribution
        - VaR and CVaR at 95% confidence
        """
        result = await self.execute(ticker, "monte_carlo", timeframe)
        return result.monte_carlo or MonteCarloResult()

    async def run_bootstrap(
        self, ticker: str, timeframe: str = "1d", samples: int = 5000
    ) -> BootstrapResult:
        """Run bootstrap validation for statistical significance.

        Tests hypothesis about returns, volatility, or correlation.
        """
        result = await self.execute(ticker, "bootstrap", timeframe)
        return result.bootstrap or BootstrapResult()

    def _parse_smc(self, output: str) -> SMCAnalysis:
        """Parse SMC analysis from Vibe output with robust extraction."""
        blocks = []
        fvg_list = []
        liquidity = []
        imbalance = 0.0
        signal = "NEUTRAL"
        confidence = 0.5

        try:
            json_match = re.search(r'\{[\s\S]*"smc"[\s\S]*\}', output)
            if json_match:
                data = json.loads(json_match.group())
                smc_data = data.get("smc", {})
                blocks = smc_data.get("order_blocks", [])
                fvg_list = smc_data.get("fair_value_gaps", [])
                liquidity = smc_data.get("liquidity_pools", [])
                imbalance = smc_data.get("order_flow_imbalance", 0.0)
                signal = smc_data.get("smart_money_signal", "NEUTRAL")
                confidence = smc_data.get("confidence", 0.5)

            signal_match = re.search(
                r"signal[:\s]+(BULLISH|BEARISH|NEUTRAL)", output, re.IGNORECASE
            )
            if signal_match:
                signal = signal_match.group(1).upper()

            confidence_match = re.search(r"confidence[:\s]+(\d+\.?\d*)", output)
            if confidence_match:
                confidence = float(confidence_match.group(1))

            block_pattern = r"(?:order[\s_-]?block|ob)[:\s]*([0-9.,]+)"
            for match in re.finditer(block_pattern, output, re.IGNORECASE):
                blocks.append({"price": match.group(1), "type": "detected"})

            fvg_pattern = r"(?:fvg|fair[\s_-]?value[\s_-]?gap)[:\s]*([0-9.,]+)"
            for match in re.finditer(fvg_pattern, output, re.IGNORECASE):
                fvg_list.append({"price": match.group(1), "type": "detected"})

            imbalance_match = re.search(
                r"(?:order[\s_-]?flow|imbalance)[:\s]*([+-]?\d+\.?\d*)", output
            )
            if imbalance_match:
                imbalance = float(imbalance_match.group(1))

        except Exception as e:
            logger.warning(f"SMC parsing error: {e}")

        return SMCAnalysis(
            institutional_order_blocks=blocks,
            fair_value_gaps=fvg_list,
            liquidity_pools=liquidity,
            order_flow_imbalance=imbalance,
            smart_money_signal=signal,
            confidence=confidence,
        )

    def _parse_monte_carlo(self, output: str) -> MonteCarloResult:
        """Parse Monte Carlo results from Vibe output."""
        result = MonteCarloResult()

        try:
            json_match = re.search(r'\{[\s\S]*"monte[_-]?carlo"[\s\S]*\}', output)
            if json_match:
                data = json.loads(json_match.group())
                mc_data = data.get("monte_carlo", {}) or data
                result.expected_return = mc_data.get("expected_return", 0.0)
                result.volatility = mc_data.get("volatility", 0.0)
                result.sharpe_ratio = mc_data.get("sharpe_ratio", 0.0)
                result.max_drawdown = mc_data.get("max_drawdown", 0.0)
                result.var_95 = mc_data.get("var_95", 0.0)
                result.cvar_95 = mc_data.get("cvar_95", 0.0)
                result.percentile_5 = mc_data.get("percentile_5", 0.0)
                result.percentile_95 = mc_data.get("percentile_95", 0.0)
                result.distribution = (
                    mc_data.get("distribution", [])
                    if isinstance(mc_data.get("distribution", []), list)
                    else []
                )

            sharpe_match = re.search(
                r"sharpe[:\s]+([+-]?\d+\.?\d*)", output, re.IGNORECASE
            )
            if sharpe_match:
                result.sharpe_ratio = float(sharpe_match.group(1))

            dd_match = re.search(
                r"max[\s_-]?drawdown[:\s]+(\d+\.?\d*)%?", output, re.IGNORECASE
            )
            if dd_match:
                result.max_drawdown = float(dd_match.group(1))

            var_match = re.search(r"var_?95[:\s]+(\d+\.?\d*)%?", output, re.IGNORECASE)
            if var_match:
                result.var_95 = float(var_match.group(1))

            return_match = re.search(
                r"expected[\s_-]?return[:\s]+([+-]?\d+\.?\d*)%?", output, re.IGNORECASE
            )
            if return_match:
                result.expected_return = float(return_match.group(1))

        except Exception as e:
            logger.warning(f"Monte Carlo parsing error: {e}")

        return result

    def _parse_bootstrap(self, output: str) -> BootstrapResult:
        """Parse bootstrap results from Vibe output."""
        result = BootstrapResult()

        try:
            json_match = re.search(r'\{[\s\S]*"bootstrap"[\s\S]*\}', output)
            if json_match:
                data = json.loads(json_match.group())
                bs_data = data.get("bootstrap", {}) or data
                result.mean_estimate = bs_data.get("mean_estimate", 0.0)
                result.std_error = bs_data.get("std_error", 0.0)
                ci = bs_data.get("confidence_interval", [0.0, 0.0])
                result.confidence_interval = (
                    (ci[0], ci[1]) if isinstance(ci, list) else (0.0, 0.0)
                )
                result.p_value = bs_data.get("p_value", 1.0)
                result.is_significant = bs_data.get("is_significant", False)

            pval_match = re.search(
                r"p[_-]?value[:\s]+(\d+\.?\d*)", output, re.IGNORECASE
            )
            if pval_match:
                result.p_value = float(pval_match.group(1))
                result.is_significant = result.p_value < 0.05

            mean_match = re.search(r"mean[:\s]+([+-]?\d+\.?\d*)", output, re.IGNORECASE)
            if mean_match:
                result.mean_estimate = float(mean_match.group(1))

            ci_match = re.search(
                r"ci[:\s]+\[?([0-9.-]+)[,\s]+([0-9.-]+)\]?", output, re.IGNORECASE
            )
            if ci_match:
                result.confidence_interval = (
                    float(ci_match.group(1)),
                    float(ci_match.group(2)),
                )

        except Exception as e:
            logger.warning(f"Bootstrap parsing error: {e}")

        return result

    async def compare_assets(
        self, tickers: List[str], timeframe: str = "1h", analysis_type: str = "smc"
    ) -> Dict[str, Any]:
        """Compare multiple assets across SMC or risk metrics."""
        results = {}

        for ticker in tickers:
            result = await self.execute(ticker, analysis_type, timeframe)
            results[ticker] = {
                "success": result.success,
                "smc": result.smc,
                "monte_carlo": result.monte_carlo,
            }

        return results


def _safe_confidence_from_result(result: Dict[str, Any]) -> float:
    score = result.get("smart_money_score", 0)
    try:
        return max(min(float(score) / 100.0, 1.0), 0.0)
    except (TypeError, ValueError):
        return 0.0


quantic_agent = QuanticAnalysisAgent()
