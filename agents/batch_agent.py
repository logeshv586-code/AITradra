import asyncio
import json
import os
import schedule
import time
from datetime import datetime
from core.config import settings
import yfinance as yf
from agents.base_agent import BaseAgent, AgentContext
from agents.data_agent import DataAgent
from agents.blob_agent import BlobAgent
from agents.rag_agent import RagAgent

class BatchAgent(BaseAgent):
    """
    Agent 11: Batch Processing Agent.
    Runs nightly jobs for S&P 500 stocks. Updates Blobs and RAG index.
    """
    
    def __init__(self, memory=None, improvement_engine=None):
        super().__init__(name="BatchAgent", memory=memory, improvement_engine=improvement_engine)
        self.watchlist = ["AAPL", "TSLA", "MSFT", "NVDA", "META", "AMZN", "GOOGL", "NFLX"] # Mock S&P 500 subset
        self.data_agent = DataAgent()
        self.blob_agent = BlobAgent()
        self.rag_agent = RagAgent()
        
    async def run_nightly_batch(self):
        """Sequential nightly processing for all stocks in the high-fidelity watchlist."""
        print(f"[{datetime.now()}] STARTING NIGHTLY BATCH PROCESS...")
        for symbol in self.watchlist:
            try:
                print(f"-> Processing {symbol}")
                # 1. Collect
                ctx = AgentContext(task=f"Fetch {symbol}", ticker=symbol)
                data_ctx = await self.data_agent.run(ctx)
                
                # 2. Persist
                await self.blob_agent.run(AgentContext(task=f"Save {symbol}", ticker=symbol, metadata={"blob_data": data_ctx.result}))
                
                # 3. Index
                await self.rag_agent.run(AgentContext(task=f"Index {symbol}", ticker=symbol, metadata={"blob_data": data_ctx.result}))
                
            except Exception as e:
                print(f"Error processing {symbol} in batch: {e}")
        
        self.rag_agent.save_index()
        print(f"[{datetime.now()}] NIGHTLY BATCH COMPLETE.")

    async def run_historical_backfill(self):
        """Massive background collection loop for Omni-Data past/present trends."""
        print(f"[{datetime.now()}] 🌐 OMNI-DATA HISTORICAL BACKFILL INITIATED...")
        
        # Scrape maximum historical dataset for the 50+ global assets
        for symbol in settings.DEFAULT_WATCHLIST:
            try:
                print(f"-> Archiving historical trend data for {symbol}")
                
                # Fetch 1-year historical dataset using yfinance to satisfy "past and present data"
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1y")
                
                # 1. Persist to blob storage
                metadata = {
                    "source": "yfinance_1y",
                    "rows": len(hist),
                    "latest_close": round(float(hist['Close'].iloc[-1]), 2) if not hist.empty else 0
                }
                await self.blob_agent.run(AgentContext(task=f"Archive History {symbol}", ticker=symbol, metadata=metadata))
                
                # 2. Index for RAG semantic search
                await self.rag_agent.run(AgentContext(task=f"Index Trend {symbol}", ticker=symbol, metadata=metadata))
                
            except Exception as e:
                print(f"Error archiving {symbol} history: {e}")
                
        self.rag_agent.save_index()
        print(f"[{datetime.now()}] 🌐 OMNI-DATA BACKFILL COMPLETE.")

    async def observe(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, f"Observing batch trigger: {context.task}")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, "Planning batch execution.")
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, "Validating batch targets.")
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, "Reflecting on batch completion.")
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, "Executing high-throughput batch intelligence extraction.")
        
        if "history" in context.task.lower() or "backfill" in context.task.lower():
            await self.run_historical_backfill()
            context.result = {"status": "omni_data_backfill_complete", "stocks_processed": len(settings.DEFAULT_WATCHLIST)}
        else:
            await self.run_nightly_batch()
            context.result = {"status": "batch_complete", "stocks_processed": len(self.watchlist)}
            
        return context

# SCHEDULER (Simulation)
def start_scheduler():
    agent = BatchAgent()
    
    def run_job():
        asyncio.run(agent.run_nightly_batch())
    
    schedule.every().day.at("01:00").do(run_job)
    print("AXIOM Batch Scheduler ONLINE. Awaiting 01:00 trigger.")
    
    # In a real daemon this would be a while loop
    # while True:
    #     schedule.run_pending()
    #     time.sleep(60)

if __name__ == "__main__":
    async def test():
        agent = BatchAgent()
        await agent.run(AgentContext(task="Manual Batch Run"))
    
    asyncio.run(test())
