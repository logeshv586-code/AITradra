"""SessionManager — Per-stock independent chat sessions with conversation memory.

Each stock clicked on the globe creates a new session pre-loaded with that stock's
RAG context. Sessions maintain conversation history for multi-turn chat.
"""

import uuid
import time
from datetime import datetime
from typing import Optional
from core.logger import get_logger

logger = get_logger(__name__)

# Session TTL: 30 minutes of inactivity
SESSION_TTL_SECONDS = 1800


class ChatSession:
    """Individual chat session for a specific stock."""

    def __init__(self, ticker: str, session_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.ticker = ticker
        self.messages: list[dict] = []
        self.rag_context: list[dict] = []
        self.stock_data: dict = {}
        self.created_at = time.time()
        self.last_active = time.time()

    def add_message(self, role: str, content: str) -> dict:
        """Add a message to the conversation history."""
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        self.messages.append(msg)
        self.last_active = time.time()
        return msg

    def get_conversation_context(self, max_messages: int = 10) -> str:
        """Build conversation context string for the LLM prompt."""
        recent = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
        lines = []
        for msg in recent:
            role_label = "User" if msg["role"] == "user" else "OMNI-DATA"
            lines.append(f"{role_label}: {msg['content']}")
        return "\n".join(lines)

    def is_expired(self) -> bool:
        return (time.time() - self.last_active) > SESSION_TTL_SECONDS

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "ticker": self.ticker,
            "message_count": len(self.messages),
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "last_active": datetime.fromtimestamp(self.last_active).isoformat(),
            "is_expired": self.is_expired(),
        }


class SessionManager:
    """Manages all active per-stock chat sessions."""

    def __init__(self):
        self._sessions: dict[str, ChatSession] = {}  # session_id -> ChatSession
        self._ticker_sessions: dict[str, list[str]] = {}  # ticker -> [session_ids]
        logger.info("SessionManager initialized")

    def create_session(self, ticker: str) -> ChatSession:
        """Create a new chat session for a stock."""
        session = ChatSession(ticker=ticker.upper())

        # Store session
        self._sessions[session.session_id] = session
        if ticker.upper() not in self._ticker_sessions:
            self._ticker_sessions[ticker.upper()] = []
        self._ticker_sessions[ticker.upper()].append(session.session_id)

        # Add welcome message
        session.add_message("assistant",
            f"Hi! I'm your dedicated AI analyst for **{ticker.upper()}**. "
            f"Ask me anything — past performance, today's move, price prediction, "
            f"fundamentals, risk analysis, or comparison with peers. "
            f"I have access to historical data, news, and market intelligence."
        )

        logger.info(f"New session created: {session.session_id} for {ticker.upper()}")

        # Clean expired sessions periodically
        self._cleanup_expired()

        return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID. Returns None if expired or not found."""
        session = self._sessions.get(session_id)
        if session and session.is_expired():
            self._remove_session(session_id)
            return None
        return session

    def get_or_create_session(self, ticker: str, session_id: str = None) -> ChatSession:
        """Get existing session or create a new one."""
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session

        return self.create_session(ticker)

    def get_sessions_for_ticker(self, ticker: str) -> list[dict]:
        """Get all active sessions for a ticker."""
        ticker = ticker.upper()
        session_ids = self._ticker_sessions.get(ticker, [])
        active = []
        for sid in session_ids:
            session = self.get_session(sid)
            if session:
                active.append(session.to_dict())
        return active

    def _remove_session(self, session_id: str):
        """Remove a session."""
        session = self._sessions.pop(session_id, None)
        if session:
            ticker_list = self._ticker_sessions.get(session.ticker, [])
            if session_id in ticker_list:
                ticker_list.remove(session_id)

    def _cleanup_expired(self):
        """Remove all expired sessions."""
        expired = [sid for sid, s in self._sessions.items() if s.is_expired()]
        for sid in expired:
            self._remove_session(sid)
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

    def get_active_count(self) -> int:
        self._cleanup_expired()
        return len(self._sessions)


# Global singleton
session_manager = SessionManager()
