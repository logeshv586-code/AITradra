import asyncio
import sys
import os
sys.path.append(os.getcwd())

from gateway.knowledge_store import knowledge_store

async def get_latest_verdict(ticker="BTC-USD"):
    intel = knowledge_store.get_ticker_intelligence(ticker)
    if not intel:
        print(f"No intelligence found for {ticker}")
        return

    print(f"\n🚀 FINAL SYSTEM VERDICT: {ticker}")
    print(f"Recommendation: {intel.get('recommendation')}")
    print(f"Confidence: {intel.get('confidence_score')}%")
    print(f"Composite Score: {intel.get('analysis', {}).get('composite_score', 'N/A')}")
    
    print(f"\n🔍 AGENT SIGNALS:")
    agents = intel.get("agents", {})
    for name, data in agents.items():
        print(f"   • {name.upper()}: {data.get('signal')} (Score: {data.get('score')})")
        print(f"     Summary: {data.get('summary')[:100]}...")

    print(f"\n📡 TOP HEADLINES:")
    for h in intel.get("top_headlines", [])[:3]:
        print(f"   • {h.get('headline')} (Sentiment: {h.get('sentiment_score')})")

if __name__ == "__main__":
    asyncio.run(get_latest_verdict("BTC-USD"))
