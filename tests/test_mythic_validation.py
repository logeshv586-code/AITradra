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

    with open(app.state.memory.structured.log_path, "r", encoding="utf-8") as fh:
        records = json.load(fh)

    assert records[-1]["ticker"] == "AAPL"
    assert records[-1]["prediction"]["price_at_prediction"] == 188.5
