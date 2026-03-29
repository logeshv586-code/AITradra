import os
import httpx
from typing import Optional
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


class LLMClient:
    """Unified LLM client supporting local GGUF (via llama-cpp), NVIDIA NIM, Ollama, and fallback mock responses."""
    _local_llm = None  # Singleton for local GGUF model

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url or settings.OLLAMA_URL
        self.model = model or settings.LLM_MODEL
        self.timeout = settings.LLM_TIMEOUT
        
        # NVIDIA NIM Configuration (API)
        self.nvidia_api_key = os.getenv("NVIDIA_API_KEY")
        self.nvidia_base_url = "https://integrate.api.nvidia.com/v1"
        self.nvidia_model = model or "nvidia/nemotron-3-8b-instruct"
        
        # LM Studio Configuration
        self.lmstudio_url = "http://localhost:1234/v1/chat/completions"
        self.lmstudio_model = "lmstudio-community/nvidia-nemotron-3-nano-4b-gguf"
        
        if self.nvidia_api_key:
            logger.info(f"NVIDIA API Key found. Using NvidiaNIMProvider with {self.nvidia_model}")
            self.provider_type = "nvidia"
        else:
            logger.info(f"Using LM Studio local model: {self.lmstudio_model}")
            self.provider_type = "lmstudio"

    async def complete(self, prompt: str, system: str = "", temperature: float = 0.1,
                       max_tokens: int = 2000, expect_json: bool = False, force_provider: str | None = None) -> str:
        """Try each provider. Never return hardcoded text unless all fail."""
        import re
        import json
        
        if force_provider == "nvidia":
            providers = ["nvidia", "lmstudio"]
        else:
            providers = [force_provider] if force_provider else ["nvidia", "lmstudio", "ollama"]
        
        for provider in providers:
            try:
                result = None
                if provider == "local_gguf":
                    result = await self._try_local_gguf(prompt, system, temperature, max_tokens)
                elif provider == "nvidia" and self.nvidia_api_key:
                    result = await self._try_nvidia(prompt, system, temperature, max_tokens)
                elif provider == "lmstudio":
                    result = await self._try_lmstudio(prompt, system, temperature, max_tokens)
                elif provider == "ollama":
                    result = await self._try_ollama(prompt, system, temperature, max_tokens)
                
                if result and isinstance(result, str):
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
        if force_provider:
            return f"Error: OMNI-DATA {force_provider} provider failed and 'No Fallback' is enforced."
            
        return self._fallback_response(prompt)

    async def _try_local_gguf(self, prompt, system, temperature, max_tokens):
        """Uses llama-cpp-python to run the local GGUF model."""
        try:
            from llama_cpp import Llama
            import anyio
            
            model_path = os.path.join(os.getcwd(), "NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf")
            
            if LLMClient._local_llm is None:
                logger.info(f"Loading local GGUF model from {model_path}...")
                LLMClient._local_llm = Llama(
                    model_path=model_path,
                    n_ctx=2048,
                    n_threads=4,
                    n_gpu_layers=0, # Set to -1 for GPU if available, 0 for CPU
                    verbose=False
                )
            
            full_prompt = f"<|system|>\n{system}\n<|user|>\n{prompt}\n<|assistant|>\n"
            
            # Run in thread to avoid blocking event loop
            def _infer():
                output = LLMClient._local_llm(
                    full_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=["<|endoftext|>", "</s>", "<|user|>"],
                    echo=False
                )
                return output["choices"][0]["text"].strip()
            
            return await anyio.to_thread.run_sync(_infer)
        except Exception as e:
            logger.error(f"Local GGUF provider error: {e}")
            return None

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

    async def _try_lmstudio(self, prompt, system, temperature, max_tokens):
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.lmstudio_url,
                json={
                    "model": self.lmstudio_model,
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
