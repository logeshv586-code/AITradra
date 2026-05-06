"""
Skill Manager — Loads and routes skill documents to agents.

Every skill .md/.skill file in /skills is loaded at startup.
Each agent gets its relevant skill context injected into LLM prompts,
so the LLM knows exactly how to analyze, score, and respond.

Mapping:
  TechnicalSpecialist  → signal-architecture.md + trading-strategies.md
  RiskSpecialist       → risk-framework.md
  MacroSpecialist      → signal-architecture.md
  SentimentSpecialist  → signal-architecture.md
  FundamentalSpecialist → trading-strategies.md
  SignalAggregator     → signal-architecture.md
  RiskManager          → risk-framework.md
  RegimeDetector       → trading-strategies.md
  CritiqueAgent        → signal-architecture.md
  MythicOrchestrator   → SKILL.md (master platform)
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from core.logger import get_logger

logger = get_logger(__name__)

# Absolute path to the skills directory (resolves regardless of CWD)
_BASE_DIR = Path(__file__).resolve().parent.parent
SKILLS_DIR_DEFAULT = str(_BASE_DIR / "skills")

# Agent name → list of skill files (without extension)
AGENT_SKILL_MAP: Dict[str, List[str]] = {
    # Core Specialists (Wave 1)
    "TechnicalSpecialist":     ["signal-architecture", "trading-strategies"],
    "MacroSpecialist":         ["signal-architecture"],
    "FundamentalSpecialist":   ["trading-strategies"],
    # Wave 2 Specialists
    "RiskSpecialist":          ["risk-framework"],
    "SentimentSpecialist":     ["signal-architecture"],
    "SectorSpecialist":        ["trading-strategies"],
    "CatalystSpecialist":      ["signal-architecture"],
    "RegimeDetectorAgent":     ["trading-strategies", "risk-framework"],
    "BreakoutMomentumAgent":   ["trading-strategies", "signal-architecture"],
    # Decision Layer (Wave 3)
    "SignalAggregatorAgent":   ["signal-architecture", "risk-framework"],
    "RiskManagerAgent":        ["risk-framework"],
    "CritiqueAgent":           ["signal-architecture"],
    "SentimentClassifierAgent":["signal-architecture"],
    # Orchestrator
    "MythicOrchestrator":      ["SKILL", "axiom-trading-intelligence"],
    # Vibe agents
    "SwarmIntelligence":       ["trading-strategies", "signal-architecture"],
    "QuanticAnalysis":         ["signal-architecture", "risk-framework"],
    # Data agents
    "CollectorAgent":          ["data-layer"],
    "MarketRAGAgent":          ["data-layer"],
    "MoveExplainerAgent":      ["llm-prompts"],
    # Research & Strategy
    "DeepResearchAgent":       ["trading-strategies", "signal-architecture"],
    "ThinkAgent":              ["signal-architecture", "trading-strategies"],
    "HyperliquidTradingAgent": ["risk-framework", "trading-strategies"],
    "StrategyGeneratorAgent":  ["trading-strategies", "signal-architecture", "risk-framework"],
}

# Maximum chars of skill context to inject per agent (increased for richer context)
MAX_SKILL_CONTEXT_CHARS = 6000


class SkillManager:
    """Manages agent skills and provides targeted skill context for LLM prompts."""

    def __init__(self, skills_dir: str = SKILLS_DIR_DEFAULT):
        self.skills_dir = skills_dir
        self.skills: Dict[str, str] = {}
        self._condensed_cache: Dict[str, str] = {}
        self._load_skills()

    def _load_skills(self):
        """Load all markdown and .skill files from the skills directory."""
        if not os.path.exists(self.skills_dir):
            logger.warning(f"Skills directory {self.skills_dir} not found.")
            return

        loaded = 0
        for filename in os.listdir(self.skills_dir):
            # Load .md and .skill files
            if filename.endswith(".md") or filename.endswith(".skill"):
                # Strip extension to get skill name
                if filename.endswith(".skill"):
                    skill_name = filename[:-6]
                else:
                    skill_name = filename[:-3]
                path = os.path.join(self.skills_dir, filename)
                try:
                    # Try UTF-8 first, fall back to latin-1 (handles any byte)
                    content = None
                    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
                        try:
                            with open(path, "r", encoding=encoding) as f:
                                content = f.read()
                            break
                        except (UnicodeDecodeError, UnicodeError):
                            continue
                    if content is None:
                        # Last resort: read bytes and decode ignoring errors
                        with open(path, "rb") as f:
                            content = f.read().decode("utf-8", errors="replace")
                    self.skills[skill_name] = content
                    loaded += 1
                except Exception as e:
                    logger.error(f"Failed to load skill {skill_name}: {e}")

        logger.info(f"✅ Loaded {loaded} skills from {self.skills_dir}: {list(self.skills.keys())}")

    def get_skill_summary(self) -> str:
        """Returns a one-line summary of all available skills for system prompts."""
        summary = "AVAILABLE SKILLS & PLATFORM CAPABILITIES:\n"
        for name in sorted(self.skills.keys()):
            content = self.skills[name]
            # Get the first non-empty, non-header line as description
            desc = ""
            for line in content.split('\n'):
                stripped = line.strip()
                if stripped and not stripped.startswith('#') and not stripped.startswith('>'):
                    desc = stripped[:120]
                    break
            summary += f"- [{name}]: {desc}\n"
        return summary

    def get_full_skill(self, skill_name: str) -> Optional[str]:
        """Returns the full content of a specific skill."""
        return self.skills.get(skill_name)

    def get_platform_master_skill(self) -> str:
        """Returns the core SKILL.md content which describes the platform architecture."""
        # Prefer the full axiom-trading-intelligence skill if available (most complete)
        if "axiom-trading-intelligence" in self.skills:
            content = self.skills["axiom-trading-intelligence"]
            # Return first 4000 chars of the master skill
            return content[:4000]
        return self.skills.get("SKILL", "No master skill documentation found.")[:4000]

    def get_agent_skill_context(self, agent_name: str) -> str:
        """
        Returns the condensed, relevant skill context for a specific agent.

        This is the key method — it extracts the most relevant sections from
        the mapped skill files and returns a compact string suitable for
        injection into LLM system prompts.

        Args:
            agent_name: The name of the agent (e.g. "TechnicalSpecialist")

        Returns:
            Condensed skill context string, max MAX_SKILL_CONTEXT_CHARS chars
        """
        # Return from cache if already built
        if agent_name in self._condensed_cache:
            return self._condensed_cache[agent_name]

        skill_names = AGENT_SKILL_MAP.get(agent_name, [])
        if not skill_names:
            logger.debug(f"No skill mapping found for agent: {agent_name}")
            return ""

        parts = []
        budget_per_skill = MAX_SKILL_CONTEXT_CHARS // max(len(skill_names), 1)

        for skill_name in skill_names:
            content = self.skills.get(skill_name, "")
            if not content:
                logger.debug(f"Skill '{skill_name}' not found for agent '{agent_name}'")
                continue

            # Extract the most relevant sections (skip code blocks, keep rules)
            condensed = self._condense_skill(content, budget_per_skill)
            if condensed:
                parts.append(f"[SKILL: {skill_name}]\n{condensed}")

        result = "\n\n".join(parts)

        # Final trim to budget
        if len(result) > MAX_SKILL_CONTEXT_CHARS:
            result = result[:MAX_SKILL_CONTEXT_CHARS] + "\n..."

        self._condensed_cache[agent_name] = result
        if result:
            logger.debug(f"Agent '{agent_name}' skill context: {len(result)} chars from {len(parts)} skills")
        return result

    def _condense_skill(self, content: str, max_chars: int) -> str:
        """
        Extracts the most important lines from a skill document.

        Prioritizes:
        1. Headers (## sections)
        2. Lines with key terms (threshold, formula, must, signal, score)
        3. Bullet points with rules
        4. Skips code blocks and long explanations
        """
        lines = content.split("\n")
        priority_lines = []
        normal_lines = []
        in_code_block = False

        key_terms = [
            "must", "always", "never", "formula", "threshold", "weight",
            "signal", "score", "confidence", "verdict", "risk", "kelly",
            "position", "stop", "target", "regime", "circuit", "block",
            "approve", "bullish", "bearish", "neutral", "consensus",
            "buy", "sell", "hold", "entry", "exit", "sizing", "atr",
            "rsi", "macd", "sma", "ema", "adx", "bollinger", "vwap",
        ]

        for line in lines:
            stripped = line.strip()

            # Skip code blocks (keep rules, skip implementation)
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            # Skip empty lines
            if not stripped:
                continue

            # Headers always priority
            if stripped.startswith("#"):
                priority_lines.append(stripped)
                continue

            # Lines with key terms
            lower = stripped.lower()
            if any(term in lower for term in key_terms):
                priority_lines.append(stripped)
                continue

            # Bullet points (rules, requirements)
            if stripped.startswith(("-", "*", "•", "|")):
                normal_lines.append(stripped)
                continue

        # Build output: priority first, then normal, within budget
        output_lines = priority_lines[:]
        remaining = max_chars - sum(len(l) + 1 for l in output_lines)

        for line in normal_lines:
            if remaining <= 0:
                break
            output_lines.append(line)
            remaining -= len(line) + 1

        result = "\n".join(output_lines)
        return result[:max_chars] if len(result) > max_chars else result

    def get_llm_prompt_template(self, agent_type: str) -> Optional[str]:
        """
        Returns the LLM prompt template for a specific agent type
        from llm-prompts.md skill file.
        """
        prompts_content = self.skills.get("llm-prompts", "")
        if not prompts_content:
            return None

        # Find the section for this agent type
        markers = {
            "technical": "### Technical Analysis Agent",
            "risk": "### Risk Analysis Agent",
            "macro": "### Macro Analysis Agent",
            "move_explainer": "### Move Explainer Agent",
            "rag": "### RAG / Market Memory Agent",
            "synthesis": "### MythicOrchestrator Final Synthesis",
            "think": "### ThinkAgent",
        }

        marker = markers.get(agent_type)
        if not marker or marker not in prompts_content:
            return None

        # Extract content between this marker and the next ### or ---
        start = prompts_content.index(marker) + len(marker)
        remaining = prompts_content[start:]

        # Find the next section break
        end = len(remaining)
        for breaker in ["### ", "---"]:
            idx = remaining.find(breaker, 10)
            if idx != -1 and idx < end:
                end = idx

        section = remaining[:end].strip()

        # Extract content between ``` blocks
        if "```" in section:
            parts = section.split("```")
            if len(parts) >= 3:
                return parts[1].strip()

        return section

    def reload(self):
        """Hot-reload all skills (useful for development)."""
        self.skills.clear()
        self._condensed_cache.clear()
        self._load_skills()
        logger.info("Skills reloaded.")


# Global singleton instance
skill_manager = SkillManager()
