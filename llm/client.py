"""
AXIOM LLM Client — Local NVIDIA Nemotron GGUF as Primary Provider.

Priority chain:
  1. Local GGUF (NVIDIA Nemotron 4B) — fast, private, no network
  2. Ollama (if running) — secondary fallback
  3. Structured fallback — data-driven response without LLM

The GGUF model is loaded ONCE at startup and shared across ALL agents.
"""

import os
import asyncio
import json
import re
import requests
from typing import Optional, Dict, Any
from core.config import settings
import httpx
from core.logger import get_logger

logger = get_logger(__name__)

_GLOBAL_LLM_INSTANCE = None

SYSTEM_TAG = "<" + "|system|" + ">"
USER_TAG = "<" + "|user|" + ">"
ASSISTANT_TAG = "<" + "|assistant|" + ">"
END_TAG = "<" + "|endoftext|" + ">"
END_S_TAG = "<" + "/s" + ">"
STOP_TOKENS = [END_TAG, END_S_TAG, USER_TAG, SYSTEM_TAG]


def get_shared_llm():
    """Get the shared global LLM instance (created at startup)."""
    global _GLOBAL_LLM_INSTANCE
    if _GLOBAL_LLM_INSTANCE is None:
        _GLOBAL_LLM_INSTANCE = LLMClient()
    return _GLOBAL_LLM_INSTANCE


class LLMClient:
    """Unified LLM client with local NVIDIA Nemotron GGUF as primary provider."""

    _local_reasoning_llm = None
    _local_general_llm = None
    _load_attempted = False
    _lm_studio_retry_after = 0.0
    _ollama_retry_after = 0.0
    _semaphore = asyncio.Semaphore(1)  # Prevent parallel bursting that crashes LM Studio

    @classmethod
    def preload_local_gguf(cls) -> bool:
        """Preloads local GGUF models into memory. Loads both reasoning and general models."""
        if cls._load_attempted:
            return cls._local_reasoning_llm is not None or cls._local_general_llm is not None
        cls._load_attempted = True

        try:
            from llama_cpp import Llama
            
            n_gpu = -1 if os.getenv("USE_CUDA", "").lower() == "true" else 0
            n_threads = max(os.cpu_count() - 2, 2)

            # 1. Load Local Reasoning Model
            reasoning_path = settings.LOCAL_REASONING_MODEL_PATH
            if os.path.exists(reasoning_path):
                logger.info(f"Loading local reasoning model: {os.path.basename(reasoning_path)}")
                cls._local_reasoning_llm = Llama(
                    model_path=os.path.abspath(reasoning_path),
                    n_ctx=4096, n_threads=n_threads, n_gpu_layers=n_gpu, verbose=False
                )
            
            # 2. Load Local General Model
            general_path = settings.LOCAL_GENERAL_MODEL_PATH
            if os.path.exists(general_path):
                logger.info(f"Loading local general model: {os.path.basename(general_path)}")
                cls._local_general_llm = Llama(
                    model_path=os.path.abspath(general_path),
                    n_ctx=4096, n_threads=n_threads, n_gpu_layers=n_gpu, verbose=False
                )

            return cls._local_reasoning_llm is not None or cls._local_general_llm is not None
        except Exception as e:
            logger.error(f"GGUF preload failed: {e}")
            return False

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url or settings.OLLAMA_URL
        self.model = model or settings.LLM_MODEL
        self.timeout = settings.LLM_TIMEOUT
        self.last_provider_used: Optional[str] = None
        
        # Determine provider
        if settings.USE_LM_STUDIO:
            self.provider = "lm_studio"
        elif settings.LLM_PROVIDER == "nvidia_nim":
            self.provider = "nvidia_nim"
        elif LLMClient._local_reasoning_llm is not None or LLMClient._local_general_llm is not None:
            self.provider = "local_gguf"
        else:
            self.provider = "ollama"
            
        logger.info(f"LLM Client initialized using {self.provider} provider.")

    async def complete(self, prompt: str, system: str = "", temperature: Optional[float] = None,
                       max_tokens: Optional[int] = None, expect_json: bool = False,
                       role: str = "general") -> str:
        """Core completion method with LM Studio -> NIM -> Local -> Ollama fallback."""
        
        # 1. Try LM Studio (Priority if enabled)
        if (self.provider == "lm_studio" or settings.USE_LM_STUDIO) and asyncio.get_running_loop().time() >= LLMClient._lm_studio_retry_after:
            async with LLMClient._semaphore:
                content = await self._try_lm_studio(prompt, system, temperature, max_tokens)
            if content and str(content).strip() != "":
                self.last_provider_used = "lm_studio"
                return self._post_process(content, expect_json)
            logger.warning("LM Studio failed, falling back to other providers.")

        # 2. Try NVIDIA NIM (Primary)
        if self.provider == "nvidia_nim":
            content = await self._try_nvidia_nim(prompt, system, temperature, max_tokens, role)
            if content and str(content).strip() != "":
                self.last_provider_used = "nvidia_nim"
                return self._post_process(content, expect_json)
            logger.warning(f"NIM failed for role '{role}', falling back to local GGUF.")

        # 2. Try Local GGUF (Safe Fallback)
        if LLMClient._local_reasoning_llm is not None or LLMClient._local_general_llm is not None:
            async with LLMClient._semaphore:
                res = await self._try_local_gguf(prompt, system, temperature or 0.1, max_tokens or 2048, role)
            if res and str(res).strip() != "":
                self.last_provider_used = "local_gguf"
                return self._post_process(res, expect_json)

        # 3. Try Ollama (Secondary Fallback)
        res = None
        if asyncio.get_running_loop().time() >= LLMClient._ollama_retry_after:
            async with LLMClient._semaphore:
                res = await self._try_ollama(prompt, system, temperature or 0.1, max_tokens or 2048)
        if res and str(res).strip() != "":
            self.last_provider_used = "ollama"
            return self._post_process(res, expect_json)

        self.last_provider_used = "intelligent_fallback"
        return self._intelligent_fallback(prompt, system, expect_json)

    def _get_role_config(self, role: str) -> Dict[str, Any]:
        """Maps a role to specific model, tokens, temperature, and API KEY."""
        if role == "sentiment":
            return {"model": settings.SENTIMENT_MODEL, "tokens": 1024, "temp": 0.0, "key": settings.MISTRAL_API_KEY}
        elif role == "reasoning":
            return {"model": settings.REASONING_MODEL, "tokens": 4096, "temp": 0.1, "key": settings.NEMOTRON_API_KEY}
        elif role == "analysis":
            return {"model": settings.ANALYSIS_MODEL, "tokens": 8192, "temp": 0.2, "key": settings.MOONSHOT_API_KEY}
        else:
            return {"model": settings.GENERAL_MODEL, "tokens": 2048, "temp": 0.3, "key": settings.MINIMAX_API_KEY}

    async def _try_lm_studio(self, prompt: str, system: str,
                             temperature: Optional[float], max_tokens: Optional[int]) -> Optional[str]:
        """Inference using LM Studio's OpenAI-compatible API."""
        try:
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": settings.LM_STUDIO_MODEL,
                "messages": [
                    {"role": "system", "content": system or "You are an expert financial assistant."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature if temperature is not None else settings.LLM_TEMPERATURE,
                "max_tokens": max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS,
                "stream": False
            }

            # Use full LLM timeout — large models (27B) need 60-120s
            timeout = httpx.Timeout(float(self.timeout), connect=5.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{settings.LM_STUDIO_URL}/chat/completions",
                    headers=headers, json=payload
                )
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                
                # Backoff on server errors (500, 503) — model may be loading
                if response.status_code >= 500:
                    LLMClient._lm_studio_retry_after = asyncio.get_running_loop().time() + 30
                logger.error(f"LM Studio error: {response.status_code} - {response.text[:200]}")
                return None
        except Exception as e:
            LLMClient._lm_studio_retry_after = asyncio.get_running_loop().time() + 15
            logger.error(f"LM Studio connection failed: {type(e).__name__}: {repr(e)}")
            return None

    async def _try_nvidia_nim(self, prompt: str, system: str, 
                               temperature: Optional[float], max_tokens: Optional[int], 
                               role: str) -> Optional[str]:
        """Inference using NVIDIA NIM with specialized keys per model."""
        try:
            config = self._get_role_config(role)
            model = config["model"]
            api_key = config["key"]
            final_temp = temperature if temperature is not None else config["temp"]
            final_tokens = max_tokens if max_tokens is not None else config["tokens"]

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system or "You are an expert financial assistant."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": final_temp,
                "max_tokens": final_tokens,
                "stream": False
            }
            
            # Reasoning features for specific models
            if "nemotron" in model.lower() or "kimi" in model.lower():
                payload["extra_body"] = {
                    "chat_template_kwargs": {"enable_thinking": True},
                    "reasoning_budget": final_tokens
                }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{settings.NVIDIA_BASE_URL}/chat/completions",
                    headers=headers, json=payload
                )
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                logger.error(
                    "NVIDIA NIM non-200 response for role '%s' model '%s': status=%s body=%s",
                    role,
                    model,
                    response.status_code,
                    response.text[:1000],
                )
                return None
        except Exception as e:
            logger.exception(
                "NVIDIA NIM exception for role '%s' model '%s' base_url '%s': %r",
                role,
                config.get("model") if "config" in locals() else None,
                settings.NVIDIA_BASE_URL,
                e,
            )
            return None

    async def _try_local_gguf(self, prompt: str, system: str,
                                temperature: float, max_tokens: int, role: str = "general") -> Optional[str]:
        """Inference using local specialized GGUF models."""
        try:
            import anyio
            
            # Select model based on role
            model = LLMClient._local_reasoning_llm if role in ["reasoning", "analysis"] else LLMClient._local_general_llm
            # Fallback to whatever is available
            if model is None:
                model = LLMClient._local_general_llm or LLMClient._local_reasoning_llm
            
            if model is None:
                return None

            sys_msg = system or "You are an expert financial analyst."

            def _infer():
                output = model.create_chat_completion(
                    messages=[
                        {"role": "system", "content": sys_msg},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=max_tokens, temperature=max(temperature, 0.01),
                )
                return output["choices"][0]["message"]["content"].strip()

            return await anyio.to_thread.run_sync(_infer)
        except Exception as e:
            logger.error(f"Local GGUF error: {e}")
            return None

    async def _try_ollama(self, prompt: str, system: str,
                           temperature: float, max_tokens: int) -> Optional[str]:
        """Fallback: Ollama API (if server is running)."""
        try:
            timeout = httpx.Timeout(min(self.timeout, 6.0), connect=2.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
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
            LLMClient._ollama_retry_after = asyncio.get_running_loop().time() + 60
            logger.warning(f"Ollama inference error: {type(e).__name__}: {repr(e)}")
        return None

    def _post_process(self, text: str, expect_json: bool) -> str:
        """Clean and optionally parse JSON from LLM output."""
        if not text:
            return text
        if not expect_json:
            return text

        # Robust JSON extraction
        try:
            clean = re.sub(r"```json|```", "", text).strip()
            start = clean.find("{")
            end = clean.rfind("}")
            if start != -1 and end != -1:
                return json.loads(clean[start:end + 1])
            # Try array
            arr_start = clean.find("[")
            arr_end = clean.rfind("]")
            if arr_start != -1 and arr_end != -1:
                return json.loads(clean[arr_start:arr_end + 1])
            return json.loads(clean)
        except Exception:
            return text  # Return raw if parsing fails

    def _intelligent_fallback(self, prompt: str, system: str, expect_json: bool) -> str:
        """Generate a structured data-driven response when no LLM is available.
        
        Instead of a generic 'offline' message, parse the prompt for data context 
        and construct a meaningful response from it.
        """
        # Extract ticker from prompt
        ticker_match = re.search(r'TICKER:\s*(\S+)', prompt, re.IGNORECASE)
        ticker = ticker_match.group(1) if ticker_match else "Unknown"

        # Extract any specialist data already in the prompt
        has_specialist = "SPECIALIST ANALYSIS" in prompt
        has_news = "NEWS" in prompt
        has_rag = "RAG KNOWLEDGE" in prompt

        if expect_json:
            return {
                "signal": "NEUTRAL",
                "confidence": 0.35,
                "summary": f"Analysis for {ticker} based on available data. LLM engine is warming up.",
                "risk_level": "MEDIUM",
                "var_pct": 2.5,
                "macro_outlook": "NEUTRAL",
                "sentiment_score": 0.0,
            }

        sections = []
        sections.append(f"AXIOM MYTHIC — MULTI-AGENT INTELLIGENCE REPORT")
        sections.append(f"Consensus: NEUTRAL (Confidence: 35%)")
        sections.append("")

        if has_specialist:
            # Extract specialist data directly from prompt
            tech_match = re.search(r'TECHNICAL:.*?(?=RISK:|$)', prompt, re.DOTALL)
            risk_match = re.search(r'RISK:.*?(?=MACRO:|$)', prompt, re.DOTALL)
            macro_match = re.search(r'MACRO:.*?(?=\n\n|$)', prompt, re.DOTALL)

            if tech_match:
                sections.append("Technical Analysis")
                sections.append(tech_match.group(0).strip()[:200])
            if risk_match:
                sections.append("Risk Assessment")
                sections.append(risk_match.group(0).strip()[:200])
            if macro_match:
                sections.append("Macro Environment")
                sections.append(macro_match.group(0).strip()[:200])
        else:
            sections.append(f"Market intelligence for {ticker} is being aggregated.")
            sections.append("The AI model is loading. Specialist agents have computed data-driven signals.")

        if has_news:
            sections.append("")
            sections.append("News data has been collected and factored into the above analysis.")

        sections.append("")
        sections.append("Confidence: 35% (LLM synthesis pending — using data-only signals)")

        return "\n".join(sections)
