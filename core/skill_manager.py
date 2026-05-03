import os
import re
from typing import Dict, List, Optional
from core.logger import get_logger

logger = get_logger(__name__)

class SkillManager:
    """Manages agent skills and provides access to skill documentation."""
    
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = skills_dir
        self.skills: Dict[str, str] = {}
        self._load_skills()

    def _load_skills(self):
        """Load all markdown files from the skills directory."""
        if not os.path.exists(self.skills_dir):
            logger.warning(f"Skills directory {self.skills_dir} not found.")
            return

        for filename in os.listdir(self.skills_dir):
            if filename.endswith(".md"):
                skill_name = filename[:-3]
                path = os.path.join(self.skills_dir, filename)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                        self.skills[skill_name] = content
                except Exception as e:
                    logger.error(f"Failed to load skill {skill_name}: {e}")
        
        logger.info(f"Loaded {len(self.skills)} skills from {self.skills_dir}")

    def get_skill_summary(self) -> str:
        """Returns a summary of all available skills for system prompts."""
        summary = "AVAILABLE SKILLS & PLATFORM CAPABILITIES:\n"
        for name in sorted(self.skills.keys()):
            # Extract first few lines or title if possible
            content = self.skills[name]
            first_lines = content.split('\n')[:5]
            summary += f"- {name}: {' '.join(first_lines)}\n"
        return summary

    def get_full_skill(self, skill_name: str) -> Optional[str]:
        """Returns the full content of a specific skill."""
        return self.skills.get(skill_name)

    def get_platform_master_skill(self) -> str:
        """Returns the core SKILL.md content which describes the platform architecture."""
        return self.skills.get("SKILL", "No master skill documentation found.")

# Global instance
skill_manager = SkillManager()
