import asyncio
import json
import os
import schedule
import time
from datetime import datetime
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

    async def observe(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, f"Observing batch trigger: {context.task}")
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, "Executing high-throughput batch intelligence extraction.")
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
