"""LLM Client — Abstraction layer for LLM providers (Ollama, fallback)."""

import httpx
from typing import Optional
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


class LLMClient:
    """Unified LLM client supporting local Mistral GGUF, Ollama, and fallback mock responses."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        import os
        self.base_url = base_url or settings.OLLAMA_URL
        self.model = model or settings.LLM_MODEL
        self.timeout = settings.LLM_TIMEOUT
        
        # Initialize GGUF Provider automatically
        from llm.providers.mistral_gguf import MistralGGUFProvider
        model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "mistral-7b-instruct-v0.2.Q4_K_S.gguf")
        
        if os.path.exists(model_path):
            logger.info("Local Mistral GGUF model found. Using MistralGGUFProvider.")
            self.provider = MistralGGUFProvider(model_path)
        else:
            logger.warning("Mistral GGUF not found. Falling back to Ollama REST approach.")
            self.provider = None

    async def complete(self, prompt: str, system: str = "", temperature: float = 0.1,
                       max_tokens: int = 2000) -> str:
        """Send completion request to LLM provider."""
        # Use local GGUF provider if available
        if self.provider:
            import asyncio
            try:
                # Wrap synchronous llama-cpp call in an executor
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(None, self.provider.generate, prompt, system, temperature, max_tokens)
            except Exception as e:
                logger.error(f"Local Mistral failed: {e}, falling back to mock.")
                return self._fallback_response(prompt)

        # Fallback to Ollama
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "system": system,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens,
                        }
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "")
                else:
                    logger.warning(f"LLM request failed with status {response.status_code}")
                    return self._fallback_response(prompt)
        except Exception as e:
            logger.warning(f"LLM connection failed: {e}, using fallback")
            return self._fallback_response(prompt)

    def _fallback_response(self, prompt: str) -> str:
        """Generate a structured fallback when LLM is unavailable."""
        import json
        return json.dumps({
            "chain": [
                "LLM service unavailable — using rule-based fallback",
                "Analyzing available data signals",
                "Checking technical indicators alignment",
                "Assessing news sentiment direction"
            ],
            "conclusion": "Based on available signals, maintaining current analysis with reduced confidence.",
            "confidence": 0.45,
            "risks": ["LLM unavailable — analysis based on rules only"],
            "data_gaps": ["Full LLM reasoning unavailable"]
        })
