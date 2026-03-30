"""
seojoonkim/prompt-guard — runs fully locally.
No HTTP call needed if installed as Python package.
"""
import sys
import os
from fastapi import HTTPException
from core.logger import get_logger

logger = get_logger(__name__)

# Add services/prompt-guard to path if it exists
prompt_guard_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "services", "prompt-guard")
if os.path.exists(prompt_guard_path):
    sys.path.insert(0, prompt_guard_path)

class InputGuard:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(InputGuard, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, 'initialized'):
            return
            
        try:
            # Try direct Python import
            from scripts.detect import PromptGuard as PG
            self._guard = PG()
            self._mode = "local"
            logger.info("PromptGuard initialized in local mode.")
        except ImportError:
            # Fall back to HTTP if running as Docker service
            self._mode = "http"
            self._endpoint = os.getenv("PROMPT_GUARD_URL", "http://localhost:8082")
            logger.info(f"PromptGuard falling back to HTTP mode via {self._endpoint}")
            self._guard = None
        
        self.initialized = True

    async def scan(self, user_input: str) -> dict:
        if self._mode == "local" and self._guard:
            try:
                result = await asyncio.to_thread(self._guard.analyze, user_input)
                return {
                    "safe": result.action != "block",
                    "severity": getattr(result, "severity", "LOW"),
                    "action": result.action,
                    "threats": getattr(result, "threats", [])
                }
            except Exception as e:
                logger.error(f"Local PromptGuard scan failed: {e}")
                return {"safe": True, "action": "allow"} # Default to allow if security fails
        else:
            import httpx
            try:
                async with httpx.AsyncClient() as client:
                    r = await client.post(f"{self._endpoint}/scan",
                                          json={"content": user_input, "type": "analyze"},
                                          timeout=5)
                    if r.status_code == 200:
                        return r.json()
                    return {"safe": True, "action": "allow"}
            except Exception as e:
                logger.warning(f"HTTP PromptGuard scan failed: {e}")
                return {"safe": True, "action": "allow"}

    async def safe_or_raise(self, user_input: str) -> str:
        """Returns clean input or raises HTTPException"""
        result = await self.scan(user_input)
        if result.get("action") == "block":
            logger.warning(f"BLOCKED INPUT: {user_input[:100]}... | Severity: {result.get('severity')}")
            raise HTTPException(403, f"Input blocked [{result.get('severity')}]: potential injection detected")
        return user_input

# Global instance
input_guard = InputGuard()
