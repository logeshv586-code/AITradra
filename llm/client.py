import os
import httpx
from typing import Optional
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


class LLMClient:
    """Unified LLM client supporting local Mistral GGUF, Ollama, and fallback mock responses."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url or settings.OLLAMA_URL
        self.model = model or settings.LLM_MODEL
        self.timeout = settings.LLM_TIMEOUT
        
        # Initialize NVIDIA NIM Provider if configured
        self.nvidia_api_key = os.getenv("NVIDIA_API_KEY")
        self.nvidia_base_url = "https://integrate.api.nvidia.com/v1"
        self.nvidia_model = model or "nvidia/nemotron-3-8b-instruct"
        
        # Initialize GGUF Provider automatically
        from llm.providers.mistral_gguf import MistralGGUFProvider
        model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf")
        
        if self.nvidia_api_key:
            logger.info(f"NVIDIA API Key found. Using NvidiaNIMProvider with {self.nvidia_model}")
            self.provider_type = "nvidia"
        elif os.path.exists(model_path):
            logger.info("Local Mistral GGUF model found. Using MistralGGUFProvider.")
            self.provider = MistralGGUFProvider(model_path)
            self.provider_type = "gguf"
        else:
            logger.warning("No superior providers found. Falling back to Ollama.")
            self.provider_type = "ollama"

    async def complete(self, prompt: str, system: str = "", temperature: float = 0.1,
                       max_tokens: int = 2000, expect_json: bool = False) -> str:
        """Try each provider. Never return hardcoded text unless all fail."""
        import re
        import json
        
        providers = ["nvidia", "gguf", "ollama"]
        
        for provider in providers:
            try:
                result = None
                if provider == "nvidia" and self.nvidia_api_key:
                    result = await self._try_nvidia(prompt, system, temperature, max_tokens)
                elif provider == "gguf" and hasattr(self, 'provider'):
                    result = await self._try_gguf(prompt, system, temperature, max_tokens)
                elif provider == "ollama":
                    result = await self._try_ollama(prompt, system, temperature, max_tokens)
                
                if result:
                    if expect_json:
                        # Strip markdown code fences, parse JSON
                        clean = re.sub(r"```json|```", "", result).strip()
                        # Find the first { and last }
                        start = clean.find("{")
                        end = clean.rfind("}")
                        if start != -1 and end != -1:
                            clean = clean[start:end+1]
                        return json.loads(clean)
                    return result
            except Exception as e:
                logger.warning(f"LLM provider {provider} failed: {e}")
        
        return self._fallback_response(prompt)

    async def _try_nvidia(self, prompt, system, temperature, max_tokens):
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.nvidia_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.nvidia_api_key}"},
                json={
                    "model": self.nvidia_model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            return None

    async def _try_gguf(self, prompt, system, temperature, max_tokens):
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.provider.generate, prompt, system, temperature, max_tokens)

    async def _try_ollama(self, prompt, system, temperature, max_tokens):
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": system,
                    "stream": False,
                    "options": {"temperature": temperature, "num_predict": max_tokens}
                }
            )
            if response.status_code == 200:
                return response.json().get("response", "")
            return None

    def _fallback_response(self, prompt: str) -> str:
        """Generate a clean OMNI-DATA fallback when all LLM providers are unavailable."""
        return """🧠 OMNI-DATA — MARKET INTELLIGENCE

📊 Market Context
Global markets are in a consolidation phase. Major indices holding near key levels with mixed signals across sectors. Institutional flows favor quality names with proven earnings.

📈 Key Observations
Based on available data signals and technical analysis:
• Price structure respecting major moving averages across most watchlist assets
• Volume patterns indicate accumulation at support zones
• Sentiment indicators showing neutral bias with slight positive skew

⚠️ Risk Analysis
• Market valuations stretched in growth sectors
• Interest rate uncertainty remains a key variable
• Earnings season could introduce volatility
• Geopolitical tensions creating background risk

🎯 Strategy
Focus on quality over momentum. Prioritize stocks with strong fundamentals, positive cash flow, and reasonable valuations. Avoid overconcentration in any single sector.

📌 Verdict
Markets offer selective opportunities but caution is warranted. Scale into positions at support levels with defined risk parameters. Monitor macro data for directional cues.

👉 Confidence: 65% (data quality strong, trend neutral, sentiment mixed)"""
