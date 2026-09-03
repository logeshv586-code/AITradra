from __future__ import annotations

import numpy as np
import pytest

from agents.base_agent import AgentContext
from agents.legacy.portfolio_agent.agent import PortfolioAgent
from core.config import settings


@pytest.mark.asyncio
async def test_portfolio_agent_never_exceeds_central_position_cap(monkeypatch) -> None:
    monkeypatch.setattr(settings, "MAX_POSITION_PCT", 0.03)
    prices = (100.0 * np.exp(np.cumsum(np.full(120, 0.002)))).tolist()
    context = AgentContext(task="portfolio-cap-test", ticker="TEST")
    context.observations["prices"] = prices

    agent = PortfolioAgent()
    context = await agent.observe(context)
    context = await agent.think(context)
    context = await agent.plan(context)
    context = await agent.act(context)

    assert context.result["risk_limit_position_pct"] == 3.0
    assert context.result["recommended_position_size_pct"] <= 3.0


@pytest.mark.asyncio
async def test_portfolio_fallback_respects_small_central_cap(monkeypatch) -> None:
    monkeypatch.setattr(settings, "MAX_POSITION_PCT", 0.005)
    context = AgentContext(task="portfolio-fallback-test", ticker="TEST")
    context.observations["prices"] = [100.0, 101.0]

    agent = PortfolioAgent()
    context = await agent.act(context)

    assert context.result["risk_limit_position_pct"] == 0.5
    assert context.result["recommended_position_size_pct"] <= 0.5
