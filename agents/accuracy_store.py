"""
agents/accuracy_store.py  —  Institutional Self-Correction Agent (Layer 4)
========================================================================
Background supervisor that audits research suggestions after 24 hours.
Compares predicted direction/signal vs actual market performance.
Updates agent_health weights and suggests retraining.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from agents.base_agent import BaseAgent, AgentContext
from gateway.knowledge_store import knowledge_store
from core.logger import get_logger

logger = get_logger(__name__)

class AccuracyStoreAgent(BaseAgent):
    """
    Agent 27: Self-Correction Supervisor
    Audits the accuracy of Layer 4 research suggestions.
    """
    def __init__(self):
        super().__init__("AccuracyStoreAgent")
        self.audit_interval_hours = 24

    async def observe(self, context: AgentContext) -> AgentContext:
        """Fetch pending suggestions (created >24h ago, no perf update)."""
        # We look for suggestions that were created more than 24 hours ago
        # but haven't been 'graded' yet.
        # Note: knowledge_store.get_latest_research_suggestions doesn't filter by time.
        # We'll fetch all and filter in Python for safety/simplicity.
        
        all_suggestions = knowledge_store.get_latest_research_suggestions(limit=100)
        cutoff = datetime.now() - timedelta(hours=self.audit_interval_hours)
        
        pending = []
        for s in all_suggestions:
            created_at = datetime.fromisoformat(s["created_at"])
            # If created > 24h ago and perf_1m is still the initial 'backtest' value 
            # or we want to update it with 'real forward performance'
            if created_at < cutoff:
                # We reuse the perf_1m column to store 'Actual Performance' after 24h
                # In a more advanced version, we'd have a separate 'actual_return' column.
                pending.append(s)
        
        context.observations["pending_audits"] = pending
        self._add_thought(context, f"Found {len(pending)} suggestions older than 24h awaiting audit.")
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        """Calculate binary accuracy for each pending suggestion."""
        pending = context.observations.get("pending_audits", [])
        audits = []
        
        for s in pending:
            ticker = s["ticker"]
            predicted_signal = s["signal"] # e.g., "BUY", "STRONG BUY"
            
            # Fetch actual price history
            history = knowledge_store.get_ohlcv_history(ticker, days=7)
            if not history or len(history) < 2:
                continue
                
            # Find the price at 'created_at' (approx)
            # Find the price 'now'
            # Note: For simplicity in this v1, we compare latest close to the close 24h ago.
            start_px = history[1]["close"] # Previous day (approx)
            end_px = history[0]["close"]   # Today
            
            actual_return = (end_px - start_px) / start_px
            success = False
            
            if "BUY" in predicted_signal and actual_return > 0:
                success = True
            elif "SELL" in predicted_signal and actual_return < 0:
                success = True
                
            audits.append({
                "id": s["id"],
                "ticker": ticker,
                "predicted": predicted_signal,
                "actual_return": round(actual_return * 100, 2),
                "success": success
            })
            
        context.observations["audit_results"] = audits
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        """Update database and refresh agent health metrics."""
        results = context.observations.get("audit_results", [])
        success_count = 0
        
        for audit in results:
            if audit["success"]:
                success_count += 1
            
            # Update the research suggestion with real performance
            # In Phase 1, we replace the backtest perf_1m with real 24h performance
            conn = knowledge_store._get_conn()
            conn.execute(
                "UPDATE research_suggestions SET perf_1m = ? WHERE id = ?",
                (audit["actual_return"], audit["id"])
            )
            conn.commit()
            
        # Update global Accuracy metric for Orchestrator
        accuracy_rate = (success_count / len(results)) if results else 1.0
        knowledge_store.update_agent_health(
            "MythicOrchestrator",
            status="active",
            task=f"Accuracy Audit: {accuracy_rate * 100:.1f}%",
            error=False
        )
        
        context.result = {"audited": len(results), "accuracy": accuracy_rate}
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        acc = context.result.get("accuracy", 0) * 100
        context.reflection = f"Audited {context.result.get('audited')} suggestions. Swarm accuracy: {acc:.1f}%"
        return context

def get_agent():
    return AccuracyStoreAgent()

if __name__ == "__main__":
    async def run_audit():
        agent = get_agent()
        ctx = AgentContext(task="Manual accuracy sweep")
        await agent.run(ctx)
        print(ctx.reflection)
        
    asyncio.run(run_audit())
