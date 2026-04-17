import json
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.mark.asyncio
async def test_prediction_store_persists_json_log():
    from memory.memory_manager import PredictionStore

    tmp_dir = Path(__file__).resolve().parent.parent / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    log_path = tmp_dir / f"prediction_log_{uuid.uuid4().hex}.json"
    store = PredictionStore(log_path=str(log_path))

    prediction_id = await store.save_prediction(
        {
            "ticker": "AAPL",
            "prediction": {"final_decision": "BULLISH"},
            "confidence": 0.78,
            "price_at_prediction": 187.32,
            "timestamp": "2026-04-09T00:00:00Z",
        }
    )

    assert prediction_id
    reloaded = PredictionStore(log_path=str(log_path))
    records = await reloaded.get_predictions_for_ticker("AAPL")

    assert len(records) == 1
    assert records[0]["confidence"] == 0.78
    assert records[0]["prediction"]["final_decision"] == "BULLISH"


@pytest.mark.asyncio
async def test_mythic_orchestrator_records_episode_and_specialist_details(monkeypatch):
    from agents.orchestrator import MythicOrchestrator

    orchestrator = MythicOrchestrator()

    async def fake_first_wave(ticker, data):
        return {
            "technical": {"signal": "BULLISH", "confidence": 0.8, "summary": "Trend is strong."},
            "macro": {"macro_outlook": "BEARISH", "confidence": 0.6, "summary": "Macro is cautious."},
            "fundamental": {"signal": "BULLISH", "confidence": 0.7, "summary": "Fundamentals stable."},
        }

    async def fake_second_wave(ticker, data):
        return {
            "risk": {"risk_level": "HIGH", "confidence": 0.7, "summary": "Volatility elevated."},
        }

    async def fake_synthesize(query, ticker, gathered_data, specialist_outputs, critique, confidence):
        return "Final synthesis"

    monkeypatch.setattr(orchestrator, "_run_first_wave", fake_first_wave)
    monkeypatch.setattr(orchestrator, "_run_second_wave", fake_second_wave)
    monkeypatch.setattr(orchestrator, "_synthesize_final", fake_synthesize)

    result = await orchestrator.orchestrate(
        query="Should I buy AAPL?",
        ticker="AAPL",
        gathered_data={"rag_results": [{"doc": "x"}], "news": [{"headline": "AAPL rises", "published_at": "2026-04-09T00:00:00+00:00"}]},
        session_id="test-mythic",
        research_mode="DEEP",
        history=[],
    )

    assert result["specialist_details"]["technical"]["signal"] == "BULLISH"
    assert result["critique"]["agreement_score"] >= 0
    episodes = orchestrator.get_recent_episodes("AAPL", limit=1)
    assert len(episodes) == 1
    assert episodes[0]["ticker"] == "AAPL"


@pytest.mark.asyncio
async def test_analysis_endpoint_logs_prediction_and_returns_mythic_shape(monkeypatch):
    from gateway.server import app, get_stock_analysis
    from memory.memory_manager import MemoryManager

    async def fake_snapshot(ticker, max_age_minutes=120):
        return {
            "ticker": ticker,
            "recommendation": "HOLD",
            "prediction_direction": "UP",
            "confidence_score": 72,
            "price_data": {"px": 188.5, "source_used": "cache"},
            "top_headlines": [{"headline": "Apple extends gains"}],
            "agents": {},
            "sections": {},
            "as_of": "2026-04-09T00:00:00Z",
            "analysis": {"ticker": ticker, "recommendation": "HOLD"},
        }

    async def fake_run(ctx):
        ctx.result = {
            "response": "Mythic analysis response",
            "confidence": 0.62,
            "consensus": "HOLD",
            "specialist_outputs": {
                "technical": "Bullish momentum",
                "macro": "Mixed macro",
                "risk": "High volatility",
            },
            "specialist_details": {
                "technical": {"signal": "BULLISH", "summary": "Bullish momentum"},
                "macro": {"macro_outlook": "NEUTRAL", "summary": "Mixed macro"},
                "risk": {"risk_level": "HIGH", "summary": "High volatility"},
                "quantic": {
                    "success": True,
                    "ticker": "AAPL",
                    "timeframe": "1h",
                    "smart_money_score": 76.0,
                    "smc": {
                        "signal": "BULLISH",
                        "confidence": 0.74,
                        "institutional_order_blocks": [
                            {"price": 186.4, "type": "demand_zone"}
                        ],
                        "fair_value_gaps": [],
                        "liquidity_pools": [],
                        "order_flow_imbalance": 0.32,
                    },
                    "monte_carlo": {
                        "sharpe": 1.48,
                        "max_dd": 4.2,
                        "var_95": 2.4,
                        "cvar_95": 3.1,
                        "distribution": [0.1, 0.2, 0.15],
                    },
                    "bootstrap": {
                        "mean_estimate": 0.018,
                        "std_error": 0.004,
                        "confidence_interval": [0.01, 0.03],
                        "p_value": 0.02,
                        "is_significant": True,
                    },
                    "synthesis": "Institutional flow remains constructive.",
                    "execution_time_ms": 912.0,
                },
                "vibe_swarm": {
                    "success": True,
                    "preset": "investment-committee",
                    "query": "Provide a full mythic-tier analysis for AAPL",
                    "synthesis": "Committee consensus is balanced but constructive.",
                    "agents": ["portfolio_manager", "risk_analyst"],
                    "agent_count": 2,
                    "confidence": 0.81,
                    "execution_time_ms": 1440.0,
                },
            },
            "critique": {"agreement_score": 0.62, "flags": ["RISK_CONTRADICTS_TECHNICAL"]},
            "sources_used": ["rag_results", "news"],
            "pipeline_ms": 4200,
        }
        return ctx

    monkeypatch.setattr("gateway.server.intelligence_service.get_ticker_intelligence", fake_snapshot)
    monkeypatch.setattr("gateway.server.query_router.run", fake_run)

    tmp_dir = Path(__file__).resolve().parent.parent / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    log_path = tmp_dir / f"prediction_log_{uuid.uuid4().hex}.json"

    app.state.memory = MemoryManager()
    app.state.memory.structured.log_path = str(log_path)
    app.state.memory.structured._predictions = []

    result = await get_stock_analysis("AAPL")

    assert result["TechnicalSpecialist"]["signal"] == "BULLISH"
    assert result["MacroSpecialist"]["macro_outlook"] == "NEUTRAL"
    assert result["RiskSpecialist"]["risk_level"] == "HIGH"
    assert result["FinalDecision"] == "HOLD"
    assert result["logged_to"] == "data/prediction_log.json"
    assert result["quantic"]["smart_money_score"] == 76.0
    assert result["quantic"]["smc"]["signal"] == "BULLISH"
    assert result["quantic"]["monte_carlo"]["var_95"] == 2.4
    assert result["swarm"]["agent_count"] == 2
    assert result["swarm"]["preset"] == "investment-committee"

    with open(app.state.memory.structured.log_path, "r", encoding="utf-8") as fh:
        records = json.load(fh)

    assert records[-1]["ticker"] == "AAPL"
    assert records[-1]["prediction"]["price_at_prediction"] == 188.5
