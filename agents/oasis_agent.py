"""
OASIS Agent — Swarm Intelligence scaling logic for MiroFish.
Manages 10,000+ agent profiles and handles Activity Scaling.
"""

import random
from typing import List, Dict, Any
from dataclasses import dataclass, field
from core.logger import get_logger

logger = get_logger(__name__)

@dataclass
class AgentProfile:
    id: str
    name: str
    personality: str
    background: str
    interests: List[str] = field(default_factory=list)
    state: Dict[str, Any] = field(default_factory=dict)

class OasisManager:
    """
    Manages a massive pool of 10,000+ agents.
    Uses 'Activity Scaling' to only process active agents per round.
    """

    def __init__(self, max_agents: int = 10000):
        self.max_agents = max_agents
        self.pool: Dict[str, AgentProfile] = {}
        self._initialize_pool()

    def _initialize_pool(self):
        """Pre-generate agent profiles (lazy creation in production)."""
        logger.info(f"Initializing OASIS pool with capacity: {self.max_agents}")
        # In a real scenario, we'd load these from a DB or generate them on the fly
        # For now, we seed the concept of the 10k pool
        pass

    def get_active_subset(self, context_keywords: List[str], count: int = 50) -> List[AgentProfile]:
        """
        Activity Scaling Logic:
        Select agents whose 'interests' or 'background' match the current context.
        """
        # Placeholder for semantic matching logic
        # For prototype, we return a random subset if pool is empty, 
        # but in usage we'd fetch from indexed profiles.
        
        # If pool is empty, generate a few sample ones
        if not self.pool:
            for i in range(count):
                a_id = f"agent_{i}"
                self.pool[a_id] = AgentProfile(
                    id=a_id,
                    name=f"Observer {i}",
                    personality="Analytical" if i % 2 == 0 else "Creative",
                    background="Expert in world dynamics",
                    interests=["finance", "politics", "society"]
                )
        
        return list(self.pool.values())[:count]

    def create_persona(self, seed_data: str) -> AgentProfile:
        """Dynamically generate a new persona based on real-world data."""
        # This would call an LLM to derive a personality from news/novels
        p_id = f"dynamic_{len(self.pool)}"
        new_profile = AgentProfile(
            id=p_id,
            name=f"Dynamic Persona {len(self.pool)}",
            personality="Derived from seed text",
            background=seed_data[:100],
            interests=["extracted from text"]
        )
        self.pool[p_id] = new_profile
        return new_profile

oasis_manager = OasisManager()
