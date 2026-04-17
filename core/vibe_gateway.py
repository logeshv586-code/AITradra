"""Vibe Trading AI Gateway — Bridge to vibe-trading-ai CLI and API.

Provides a unified interface to:
- Spawn swarm teams (29 presets)
- Run quantic analysis (SMC, Monte Carlo)
- Generate trading strategies (Pine Script, MQL5, Python)
- Execute backtests across 7 engines
"""

import os
import json
import asyncio
import subprocess
from typing import Optional, Dict, Any, List
from pathlib import Path

from core.logger import get_logger
from core.config import settings

logger = get_logger(__name__)

VIBE_CLI_PATH = os.environ.get("VIBE_CLI_PATH", "vibe")


class VibeGateway:
    """Gateway to interact with vibe-trading-ai CLI."""

    def __init__(self):
        self._available = self._check_availability()
        self._workspace = os.path.join(settings.DATA_DIR, "vibe_workspace")
        os.makedirs(self._workspace, exist_ok=True)

    def _check_availability(self) -> bool:
        """Check if vibe-trading-ai is installed."""
        try:
            result = subprocess.run(
                [VIBE_CLI_PATH, "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                logger.info(f"Vibe CLI available: {result.stdout.strip()}")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.warning(f"Vibe CLI not available: {e}")
        return False

    @property
    def is_available(self) -> bool:
        return self._available

    async def _run_vibe_command(
        self, args: List[str], timeout: int = 120, input_data: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a vibe CLI command with proper error handling."""
        if not self._available:
            return {
                "error": "Vibe Trading AI not installed. Run: pip install vibe-trading-ai"
            }

        try:
            cmd = [VIBE_CLI_PATH] + args
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE if input_data else None,
                cwd=self._workspace,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=input_data.encode() if input_data else None),
                timeout=timeout,
            )

            if process.returncode != 0:
                logger.error(f"Vibe command failed: {stderr.decode()}")
                return {"error": stderr.decode()}

            return {"success": True, "output": stdout.decode(), "raw": stdout.decode()}
        except asyncio.TimeoutError:
            logger.error(f"Vibe command timed out after {timeout}s")
            return {"error": f"Command timed out after {timeout}s"}
        except Exception as e:
            logger.error(f"Vibe command error: {e}")
            return {"error": str(e)}

    async def spawn_swarm(
        self, team_preset: str, query: str, market: str = "crypto"
    ) -> Dict[str, Any]:
        """Spawn a swarm team based on preset.

        Args:
            team_preset: One of 29 presets (e.g., "investment-committee", "crypto-desk")
            query: The research question or task
            market: Target market (crypto, stocks, forex, macro)

        Returns:
            Swarm response with agent contributions and synthesis
        """
        logger.info(f"Spawning Vibe swarm: {team_preset} for query: {query[:50]}...")

        args = [
            "swarm",
            "--preset",
            team_preset,
            "--query",
            query,
            "--market",
            market,
            "--output",
            "json",
        ]

        return await self._run_vibe_command(args, timeout=180)

    async def run_quantic_analysis(
        self, ticker: str, analysis_type: str = "full", timeframe: str = "1h"
    ) -> Dict[str, Any]:
        """Run quantic analysis (SMC, Monte Carlo, Bootstrap).

        Args:
            ticker: Asset symbol (e.g., "BTC", "AAPL")
            analysis_type: Type of analysis (smc, monte_carlo, bootstrap, full)
            timeframe: Data timeframe (1m, 5m, 15m, 1h, 4h, 1d)

        Returns:
            Analysis results with SMC signals, probability distributions
        """
        logger.info(f"Running quantic analysis on {ticker}: {analysis_type}")

        args = [
            "quantic",
            "--ticker",
            ticker,
            "--type",
            analysis_type,
            "--timeframe",
            timeframe,
            "--output",
            "json",
        ]

        return await self._run_vibe_command(args, timeout=300)

    async def generate_strategy(
        self, strategy描述: str, language: str = "pine", market: str = "crypto"
    ) -> Dict[str, Any]:
        """Generate trading strategy code from natural language.

        Args:
            strategy描述: Natural language strategy description
            language: Target language (pine, mql5, python, quantconnect)
            market: Target market type

        Returns:
            Generated code with comments and configuration
        """
        logger.info(f"Generating {language} strategy: {strategy描述[:50]}...")

        args = [
            "generate",
            "--description",
            strategy描述,
            "--language",
            language,
            "--market",
            market,
            "--output",
            "json",
        ]

        return await self._run_vibe_command(args, timeout=180)

    async def run_backtest(
        self,
        strategy_code: str,
        ticker: str,
        timeframe: str = "1h",
        engine: str = "composite",
    ) -> Dict[str, Any]:
        """Run backtest using one of 7 engines.

        Args:
            strategy_code: Strategy script content
            ticker: Asset to backtest
            timeframe: Data timeframe
            engine: Backtest engine (vectorbt, backtrader, tradingview,
                     hyperopt, composite, custom, live)

        Returns:
            Backtest results with metrics, equity curve, trades
        """
        logger.info(f"Running {engine} backtest on {ticker}")

        strategy_file = os.path.join(self._workspace, "strategy_temp.txt")
        with open(strategy_file, "w") as f:
            f.write(strategy_code)

        args = [
            "backtest",
            "--strategy",
            strategy_file,
            "--ticker",
            ticker,
            "--timeframe",
            timeframe,
            "--engine",
            engine,
            "--output",
            "json",
        ]

        result = await self._run_vibe_command(args, timeout=600)

        try:
            os.remove(strategy_file)
        except:
            pass

        return result

    async def cross_market_analysis(
        self, assets: List[str], query: str
    ) -> Dict[str, Any]:
        """Run analysis across multiple markets simultaneously.

        Args:
            assets: List of tickers across markets (e.g., ["BTC-USD", "SPY", "NIFTY"])
            query: Analysis question

        Returns:
            Cross-market insights with correlation data
        """
        logger.info(f"Cross-market analysis: {assets}")

        args = [
            "cross-market",
            "--assets",
            ",".join(assets),
            "--query",
            query,
            "--output",
            "json",
        ]

        return await self._run_vibe_command(args, timeout=300)

    def list_presets(self) -> List[str]:
        """Return list of available swarm presets."""
        return [
            "investment-committee",
            "crypto-trading-desk",
            "macro-research",
            "technical-analysis-team",
            "risk-management-desk",
            "news-sentiment-squad",
            "earnings-whisperers",
            "options-flow-desk",
            "portfolio-optimizers",
            "regime-detectors",
            "arbitrage-hunters",
            "backtest-warriors",
            "algo-development-squad",
            "compliance-review-board",
            "quant-research-lab",
            "market-structure-specialists",
            "liquidity-mappers",
            "order-flow-analysts",
            "divergence-detectors",
            "momentum-chasers",
            "mean-reversion-team",
            "breakout-specialists",
            "support-resistance-scouts",
            "volume-profile-squad",
            "on-chain-analysts",
            "social-sentiment-team",
            "fundamental-deep-dive",
            "catalyst-trackers",
            "seasonality-specialists",
        ]

    async def health_check(self) -> Dict[str, Any]:
        """Check vibe-trading-ai health and capabilities."""
        if not self._available:
            return {
                "status": "unavailable",
                "message": "Install vibe-trading-ai: pip install vibe-trading-ai",
            }

        result = await self._run_vibe_command(["doctor"])
        return {
            "status": "ready" if result.get("success") else "error",
            "details": result,
        }


vibe_gateway = VibeGateway()
