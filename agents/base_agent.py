"""BaseAgent — Abstract base implementing Claude Flow loop: OBSERVE → THINK → PLAN → ACT → REFLECT → IMPROVE."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime, timezone
import asyncio
import traceback
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AgentContext:
    """Context passed through the Claude Flow loop."""
    task: str
    ticker: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    observations: dict = field(default_factory=dict)
    thoughts: list[str] = field(default_factory=list)
    plan: list[str] = field(default_factory=list)
    actions_taken: list[dict] = field(default_factory=list)
    result: Any = None
    reflection: str = ""
    confidence: float = 0.0
    errors: list[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)


class BaseAgent(ABC):
    """Base agent implementing Claude Flow loop. All agents inherit this."""

    def __init__(self, name: str, memory=None, improvement_engine=None,
                 max_retries: int = 3, timeout_seconds: int = 30):
        self.name = name
        self.memory = memory
        self.improvement_engine = improvement_engine
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.logger = get_logger(f"agent.{name}")

    def _add_thought(self, context: AgentContext, thought: str):
        """Helper to log a thought and add it to the context."""
        context.thoughts.append(thought)
        self.logger.info(f"[{self.name}] THOUGHT: {thought}")

    async def _get_cross_agent_insights(self, ticker: str, hours: int = 24) -> list:
        """Retrieve recent insights from other agents stored in the knowledge store."""
        try:
            from gateway.knowledge_store import knowledge_store
            insights = knowledge_store.get_recent_insights(ticker=ticker, hours=hours)
            # Filter out own insights
            return [i for i in insights if i.get("agent_name") != self.name]
        except Exception as e:
            self.logger.warning(f"[{self.name}] Failed to fetch cross-agent insights: {e}")
            return []

    async def run(self, context: AgentContext) -> AgentContext:
        """Execute the full Claude Flow loop — the ONLY entry point."""
        self.logger.info(f"[{self.name}] Starting Claude Flow loop", task=context.task)
        try:
            context = await self._observe(context)
            context = await self._think(context)
            context = await self._plan(context)
            context = await self._act_with_retry(context)
            context = await self._reflect(context)
            await self._improve(context)
        except asyncio.TimeoutError:
            context.errors.append(f"Agent {self.name} timed out after {self.timeout_seconds}s")
            self.logger.error(f"Agent {self.name} timed out")
        except Exception as e:
            context.errors.append(f"Agent {self.name} failed: {str(e)}")
            self.logger.error(f"Agent {self.name} failed: {traceback.format_exc()}")
            await self._improve(context)
        return context

    @abstractmethod
    async def observe(self, context: AgentContext) -> AgentContext: pass
    @abstractmethod
    async def think(self, context: AgentContext) -> AgentContext: pass
    @abstractmethod
    async def plan(self, context: AgentContext) -> AgentContext: pass
    @abstractmethod
    async def act(self, context: AgentContext) -> AgentContext: pass
    @abstractmethod
    async def reflect(self, context: AgentContext) -> AgentContext: pass

    async def _observe(self, ctx: AgentContext) -> AgentContext:
        if self.memory:
            past = await self.memory.recall_relevant(ctx.task, limit=5)
            if past: ctx.observations["past_context"] = past
        return await asyncio.wait_for(self.observe(ctx), timeout=self.timeout_seconds)

    async def _think(self, ctx: AgentContext) -> AgentContext:
        return await asyncio.wait_for(self.think(ctx), timeout=self.timeout_seconds)

    async def _plan(self, ctx: AgentContext) -> AgentContext:
        return await asyncio.wait_for(self.plan(ctx), timeout=self.timeout_seconds)

    async def _act_with_retry(self, ctx: AgentContext) -> AgentContext:
        for attempt in range(self.max_retries):
            try:
                return await asyncio.wait_for(self.act(ctx), timeout=self.timeout_seconds)
            except Exception as e:
                self.logger.warning(f"[{self.name}] ACT attempt {attempt+1} failed: {e}")
                if attempt == self.max_retries - 1: raise
                await asyncio.sleep(2 ** attempt)
        return ctx

    async def _reflect(self, ctx: AgentContext) -> AgentContext:
        ctx = await asyncio.wait_for(self.reflect(ctx), timeout=self.timeout_seconds)
        if self.memory:
            await self.memory.store_episode(
                agent=self.name, task=ctx.task, result=str(ctx.result),
                reflection=ctx.reflection, confidence=ctx.confidence, errors=ctx.errors
            )
        return ctx

    async def _improve(self, ctx: AgentContext) -> None:
        if self.improvement_engine:
            await self.improvement_engine.process_agent_run(agent_name=self.name, context=ctx)
