"""MemoryManager — Hierarchical memory system (Working + Episodic + Semantic).

Three-tier memory architecture from the Claude Agent System pattern:
- Working Memory: In-memory Python dict (per-session context window)
- Episodic Memory: SQLite-backed session/run history (persistent agent_episodes table)
- Semantic Memory: Delegates to FAISS RAG for vector search
- Prediction Store: Tracks and scores predictions over time
"""

import os
import sqlite3
import json
from datetime import datetime, timezone
from typing import Any, Optional
from core.logger import get_logger

logger = get_logger(__name__)

from core.config import settings

DB_PATH = settings.KNOWLEDGE_DB_PATH
PREDICTION_LOG_PATH = os.path.join(os.path.dirname(DB_PATH), "prediction_log.json")


class EpisodicStore:
    """SQLite-backed episodic memory for persistent agent run history.
    
    Stores every agent episode (task, result, reflection, confidence, errors)
    in the `agent_episodes` SQLite table. Supports keyword search with recency.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._schema_mode = "classic"
        self._init_table()

    def _get_columns(self, conn: sqlite3.Connection) -> set[str]:
        rows = conn.execute("PRAGMA table_info(agent_episodes)").fetchall()
        return {row[1] for row in rows}

    def _init_table(self):
        """Create the agent_episodes table if it doesn't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent TEXT NOT NULL,
                    task TEXT NOT NULL,
                    result TEXT,
                    reflection TEXT,
                    confidence REAL DEFAULT 0.0,
                    errors TEXT,
                    metadata_json TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            columns = self._get_columns(conn)
            if "agent" in columns:
                self._schema_mode = "classic"
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_episodes_agent ON agent_episodes(agent)
                """)
            elif "agent_name" in columns:
                self._schema_mode = "knowledge_store"
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_episodes_agent_name ON agent_episodes(agent_name)
                """)

            if "created_at" in columns:
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_episodes_created ON agent_episodes(created_at)
                """)
            conn.commit()
            conn.close()
            logger.info(f"Episodic memory table initialized ({self._schema_mode})")
        except Exception as e:
            logger.warning(f"Episodic table init warning: {e}")

    async def save(self, episode: dict) -> None:
        """Persist an episode to SQLite."""
        try:
            conn = sqlite3.connect(self.db_path)
            timestamp = episode.get("timestamp", datetime.now(timezone.utc).isoformat())
            if self._schema_mode == "knowledge_store":
                state_payload = {
                    "reflection": episode.get("reflection", ""),
                    "confidence": episode.get("confidence", 0.0),
                    "metadata": episode.get("metadata", {}),
                }
                conn.execute(
                    """INSERT INTO agent_episodes (
                           session_id, agent_name, task, status, state_json,
                           result_json, error_log, created_at, updated_at
                       )
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        episode.get("session_id", f"memory-{int(datetime.now(timezone.utc).timestamp())}"),
                        episode.get("agent", "unknown"),
                        episode.get("task", ""),
                        "complete",
                        json.dumps(state_payload, default=str)[:3000],
                        json.dumps(episode.get("result", ""), default=str)[:5000],
                        json.dumps(episode.get("errors", []), default=str),
                        timestamp,
                        timestamp,
                    )
                )
            else:
                conn.execute(
                    """INSERT INTO agent_episodes (agent, task, result, reflection, confidence, errors, metadata_json, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        episode.get("agent", "unknown"),
                        episode.get("task", ""),
                        json.dumps(episode.get("result", ""), default=str)[:5000],
                        episode.get("reflection", ""),
                        episode.get("confidence", 0.0),
                        json.dumps(episode.get("errors", []), default=str),
                        json.dumps(episode.get("metadata", {}), default=str)[:2000],
                        timestamp,
                    )
                )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Episodic save failed: {e}")

    async def search(self, query: str, limit: int = 5) -> list:
        """Search episodic memory by keyword matching (recent first)."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            if self._schema_mode == "knowledge_store":
                results = conn.execute(
                    """SELECT
                           agent_name AS agent,
                           task,
                           result_json AS result,
                           state_json AS reflection,
                           0.0 AS confidence,
                           created_at
                       FROM agent_episodes
                       WHERE task LIKE ? OR result_json LIKE ? OR state_json LIKE ?
                       ORDER BY created_at DESC LIMIT ?""",
                    (f"%{query}%", f"%{query}%", f"%{query}%", limit)
                ).fetchall()
            else:
                results = conn.execute(
                    """SELECT agent, task, result, reflection, confidence, created_at
                       FROM agent_episodes
                       WHERE task LIKE ? OR result LIKE ? OR reflection LIKE ?
                       ORDER BY created_at DESC LIMIT ?""",
                    (f"%{query}%", f"%{query}%", f"%{query}%", limit)
                ).fetchall()
            conn.close()
            return [dict(r) for r in results]
        except Exception as e:
            logger.warning(f"Episodic search failed: {e}")
            return []

    async def get_recent(self, agent: str = None, limit: int = 10) -> list:
        """Get recent episodes, optionally filtered by agent name."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            if self._schema_mode == "knowledge_store":
                if agent:
                    results = conn.execute(
                        "SELECT * FROM agent_episodes WHERE agent_name = ? ORDER BY created_at DESC LIMIT ?",
                        (agent, limit)
                    ).fetchall()
                else:
                    results = conn.execute(
                        "SELECT * FROM agent_episodes ORDER BY created_at DESC LIMIT ?",
                        (limit,)
                    ).fetchall()
            else:
                if agent:
                    results = conn.execute(
                        "SELECT * FROM agent_episodes WHERE agent = ? ORDER BY created_at DESC LIMIT ?",
                        (agent, limit)
                    ).fetchall()
                else:
                    results = conn.execute(
                        "SELECT * FROM agent_episodes ORDER BY created_at DESC LIMIT ?",
                        (limit,)
                    ).fetchall()
            conn.close()
            return [dict(r) for r in results]
        except Exception as e:
            logger.warning(f"Episodic get_recent failed: {e}")
            return []

    async def count(self) -> int:
        """Get total number of episodes stored."""
        try:
            conn = sqlite3.connect(self.db_path)
            count = conn.execute("SELECT COUNT(*) FROM agent_episodes").fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0


class WorkingMemory:
    """In-memory context window for current session (short-term memory)."""

    def __init__(self, max_items: int = 100):
        self._store: dict[str, Any] = {}
        self._max = max_items
        self._conversation: list[dict] = []

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value
        if len(self._store) > self._max:
            oldest = next(iter(self._store))
            del self._store[oldest]

    def get(self, key: str) -> Any:
        return self._store.get(key)

    def add_turn(self, role: str, content: str) -> None:
        """Add a conversation turn to working memory."""
        self._conversation.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        # Auto-compact: keep last 20 turns
        if len(self._conversation) > 20:
            self._conversation = self._conversation[-15:]

    def get_conversation(self, limit: int = 10) -> list:
        """Get recent conversation turns."""
        return self._conversation[-limit:]

    def clear(self) -> None:
        self._store.clear()
        self._conversation.clear()


class PredictionStore:
    """JSON-backed prediction storage for scoring and later resolution."""

    def __init__(self, log_path: str = PREDICTION_LOG_PATH):
        self.log_path = log_path
        self._predictions = []
        self._load()

    def _load(self) -> None:
        try:
            if not os.path.exists(self.log_path):
                self._predictions = []
                return
            with open(self.log_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            self._predictions = payload if isinstance(payload, list) else []
        except Exception as e:
            logger.warning(f"Prediction log load failed: {e}")
            self._predictions = []

    def _persist(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            with open(self.log_path, "w", encoding="utf-8") as fh:
                json.dump(self._predictions, fh, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Prediction log persist failed: {e}")

    async def save_prediction(self, pred: dict) -> str:
        import uuid
        pred_id = str(uuid.uuid4())
        pred["id"] = pred_id
        self._predictions.append(pred)
        self._persist()
        return pred_id

    async def get_predictions_for_ticker(self, ticker: str, limit: int = 10) -> list:
        return [p for p in reversed(self._predictions) if p.get("ticker") == ticker][:limit]

    async def update_outcome(self, pred_id: str, actual_price: float, accuracy_score: float) -> None:
        for p in self._predictions:
            if p.get("id") == pred_id:
                p["actual_price"] = actual_price
                p["accuracy_score"] = accuracy_score
                p["resolved_at"] = datetime.now(timezone.utc).isoformat()
                break
        self._persist()


class SemanticMemory:
    """Delegates to FAISS RAG for vector-based semantic search."""

    async def search(self, query: str, n_results: int = 5) -> list:
        """Search FAISS for semantically similar documents."""
        try:
            from agents.rag_agent import RagAgent
            from agents.base_agent import AgentContext
            rag = RagAgent()
            try:
                rag.load_index()
            except Exception:
                pass
            ctx = AgentContext(task=query, metadata={"k": n_results})
            result = await rag.run(ctx)
            return result.result if isinstance(result.result, list) else []
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return []


class MemoryManager:
    """Unified memory interface — 3-tier hierarchical memory system.
    
    Working → Short-term in-memory (Python dict + conversation turns)
    Episodic → SQLite-backed persistent agent history
    Semantic → FAISS vector search (via RAG agent)
    Predictions → In-memory prediction tracking
    """

    def __init__(self):
        self.episodic = EpisodicStore()
        self.working = WorkingMemory()
        self.semantic = SemanticMemory()
        self.structured = PredictionStore()

    async def initialize(self) -> None:
        episode_count = await self.episodic.count()
        logger.info(f"Memory system initialized. Episodic episodes: {episode_count}")

    async def store_episode(self, agent: str, task: str, result: str,
                           reflection: str, confidence: float, errors: list) -> None:
        await self.episodic.save({
            "agent": agent, "task": task, "result": result,
            "reflection": reflection, "confidence": confidence,
            "errors": errors, "timestamp": datetime.now(timezone.utc).isoformat()
        })

    async def store_prediction(self, ticker: str, prediction: dict,
                              reasoning: str, confidence: float) -> str:
        return await self.structured.save_prediction({
            "ticker": ticker, "prediction": prediction,
            "reasoning": reasoning, "confidence": confidence,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def recall_relevant(self, query: str, limit: int = 5) -> list:
        """Search BOTH episodic (keyword) and semantic (vector) memory."""
        ep_results = await self.episodic.search(query, limit)
        return ep_results

    async def semantic_search(self, query: str, n_results: int = 5) -> list:
        return await self.semantic.search(query, n_results)

    async def get_past_predictions(self, ticker: str, limit: int = 10) -> list:
        return await self.structured.get_predictions_for_ticker(ticker, limit)

    async def update_prediction_outcome(self, prediction_id: str,
                                        actual_price: float, accuracy_score: float) -> None:
        await self.structured.update_outcome(prediction_id, actual_price, accuracy_score)

    def set_working_context(self, key: str, value: Any) -> None:
        self.working.set(key, value)

    def get_working_context(self, key: str) -> Any:
        return self.working.get(key)

    def add_conversation_turn(self, role: str, content: str) -> None:
        """Add a turn to working memory conversation."""
        self.working.add_turn(role, content)

    def get_conversation(self, limit: int = 10) -> list:
        """Get recent conversation from working memory."""
        return self.working.get_conversation(limit)

    async def get_system_status(self) -> dict:
        """Return memory system health status."""
        return {
            "episodic_episodes": await self.episodic.count(),
            "working_memory_keys": len(self.working._store),
            "conversation_turns": len(self.working._conversation),
            "predictions_tracked": len(self.structured._predictions),
        }
