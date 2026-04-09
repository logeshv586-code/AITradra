import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from agents.sentiment_classifier import SentimentClassifierAgent, AgentContext

async def test_sentiment_agent():
    agent = SentimentClassifierAgent()
    ctx = AgentContext(
        task="Analyze sentiment for NVDA",
        ticker="NVDA",
        observations={
            "news": [
                {"headline": "NVIDIA is dominating the AI chip market", "score": 0.9},
                {"headline": "Major tech companies increase orders for Blackwell chips", "score": 0.8},
                {"headline": "Competitors struggle to keep up with NVIDIA's pace", "score": 0.7}
            ]
        }
    )
    
    print("Running Sentiment Classifier Agent...")
    try:
        updated_ctx = await agent.run(ctx)
        print(f"Result: {updated_ctx.result}")
    except Exception as e:
        print(f"Agent execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_sentiment_agent())
