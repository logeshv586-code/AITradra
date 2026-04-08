import asyncio
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from agents.base_agent import AgentContext
from agents.orchestrator import mythic_orchestrator
from gateway.intelligence_service import intelligence_service
from core.logger import get_logger

logger = get_logger("AnalysisExecution")

async def run_comprehensive_analysis(ticker="BTC-USD"):
    print(f"\n{'='*60}")
    print(f"🚀 STARTING COMPREHENSIVE MULTI-AGENT ANALYSIS: {ticker}")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"{'='*60}\n")

    # Step 1: Intelligence Snapshot
    print(f"🔍 STEP 1: Fetching Market Intelligence Snapshot...")
    snapshot = await intelligence_service.refresh_ticker_intelligence(ticker)
    print(f"   [Snapshot] Recommendation: {snapshot.get('recommendation')}")
    print(f"   [Snapshot] Confidence: {snapshot.get('confidence_score')}%")
    print(f"   [Snapshot] Primary Driver: {snapshot.get('primary_driver')}")
    print("-" * 40)

    # Step 2: Mythic Orchestration (Ask Every Agent)
    print(f"🧠 STEP 2: Triggering Mythic Orchestrator (14-Agent Pipeline)...")
    # Simulate gathered data
    gathered_data = {
        "price_data": snapshot.get("price_data", {}),
        "history": snapshot.get("price_data", {}).get("ohlcv", []),
        "news": snapshot.get("top_headlines", []),
        "sentiment": snapshot.get("sentiment", {})
    }
    
    result = await mythic_orchestrator.orchestrate(
        query=f"Should I buy {ticker} right now based on current institutional data?",
        ticker=ticker,
        gathered_data=gathered_data,
        research_mode="DEEP"
    )
    
    print(f"\n📋 SPECIALIST OUTPUTS:")
    for agent, summary in result.get("specialist_outputs", {}).items():
        print(f"   • {agent.upper()}: {summary[:120]}...")

    print(f"\n⚖️ DECISION LAYER:")
    print(f"   • Consensus: {result.get('consensus')}")
    print(f"   • Confidence: {result.get('confidence')*100:.1f}%")
    
    print(f"\n💬 FINAL SYNTHESIS:")
    print(result.get("response", "No response generated."))
    
    print(f"\n{'='*60}")
    print(f"✅ ANALYSIS COMPLETE")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Run analysis for BTC-USD
    try:
        asyncio.run(run_comprehensive_analysis("BTC-USD"))
    except Exception as e:
        print(f"Error during analysis: {e}")
