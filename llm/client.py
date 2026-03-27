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
        model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "mistral-7b-instruct-v0.2.Q4_K_S.gguf")
        
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
                       max_tokens: int = 2000) -> str:
        """Send completion request to LLM provider."""
        # NVIDIA NIM (OpenAI-compatible)
        if self.provider_type == "nvidia":
            try:
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
                    else:
                        logger.warning(f"NVIDIA NIM failed: {response.text}")
                        self.provider_type = "ollama"  # Immediate fallback
            except Exception as e:
                logger.error(f"NVIDIA NIM connection error: {e}")
                self.provider_type = "ollama"

        # Local GGUF Provider
        if self.provider_type == "gguf":
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(None, self.provider.generate, prompt, system, temperature, max_tokens)
            except Exception as e:
                logger.error(f"Local Mistral failed: {e}")
                self.provider_type = "ollama"

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
                        "options": {"temperature": temperature, "num_predict": max_tokens}
                    }
                )
                if response.status_code == 200:
                    return response.json().get("response", "")
        except Exception as e:
            logger.warning(f"Ollama failed: {e}")
            
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
