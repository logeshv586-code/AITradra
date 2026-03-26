"""Structured Memory — SQLAlchemy ORM models."""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class PredictionRecord(Base):
    """SQLAlchemy model for agent predictions and scoring."""
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), index=True, nullable=False)
    agent_name = Column(String(50), nullable=False)
    
    # Context
    prediction_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolution_time = Column(DateTime, nullable=False)
    
    # The Prediction
    predicted_direction = Column(String(20))  # BULLISH, BEARISH
    predicted_target_price = Column(Float)
    confidence = Column(Float)
    reasoning_chain = Column(JSON)
    
    # The Resolution
    is_resolved = Column(Boolean, default=False)
    actual_price = Column(Float, nullable=True)
    accuracy_score = Column(Float, nullable=True)  # 0.0 to 1.0


class AgentExperience(Base):
    """SQLAlchemy model for episodic memory metadata."""
    __tablename__ = "agent_experiences"

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(50), index=True, nullable=False)
    task_hash = Column(String(64), index=True)
    
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    success = Column(Boolean)
    error_log = Column(JSON)
    reflection = Column(String(1000))
