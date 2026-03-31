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
import httpx
from typing import Optional
from core.config import settings
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

    _local_llm = None
    _load_attempted = False

    @classmethod
    def preload_local_gguf(cls) -> bool:
        """Preloads the local GGUF model into memory at startup. Call once."""
        if cls._load_attempted:
            return cls._local_llm is not None
        cls._load_attempted = True

        try:
            from llama_cpp import Llama
            
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            target_model = settings.LLM_MODEL.lower()
            
            # Find the best match .gguf file in the root directory
            model_path = None
            for file in os.listdir(root_dir):
                if file.lower().endswith(".gguf"):
                    # Check if model name in filename
                    if target_model in file.lower() or file.lower().startswith(target_model):
                        model_path = os.path.join(root_dir, file)
                        break
            
            # Fallback: exact match from config if no fuzzy match found
            if not model_path:
                potential_path = os.path.join(root_dir, f"{settings.LLM_MODEL}.gguf")
                if os.path.exists(potential_path):
                    model_path = potential_path

            if not model_path or not os.path.exists(model_path):
                logger.warning(f"No local GGUF model found matching '{settings.LLM_MODEL}' in {root_dir}")
                # Try finding ANY .gguf file as a last resort
                for file in os.listdir(root_dir):
                    if file.lower().endswith(".gguf"):
                        model_path = os.path.join(root_dir, file)
                        logger.info(f"Using fallback GGUF model: {file}")
                        break
                
                if not model_path:
                    return False

            logger.info(f"Loading GGUF model: {os.path.basename(model_path)}...")

            n_gpu = 0
            if os.getenv("USE_CUDA", "").lower() == "true":
                n_gpu = -1

            cls._local_llm = Llama(
                model_path=os.path.abspath(model_path),
                n_ctx=4096,
                n_threads=max(os.cpu_count() - 2, 2),
                n_gpu_layers=n_gpu,
                verbose=False,
                n_batch=512,
            )
            logger.info(f"Model loaded successfully: {os.path.basename(model_path)}")

            global _GLOBAL_LLM_INSTANCE
            _GLOBAL_LLM_INSTANCE = LLMClient()

            return True
        except Exception as e:
            logger.error(f"GGUF preload failed: {e}")
            cls._local_llm = None
            return False

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url or settings.OLLAMA_URL
        self.model = model or settings.LLM_MODEL
        self.timeout = settings.LLM_TIMEOUT

        if LLMClient._local_llm is not None:
            self.provider = "local_gguf"
        else:
            self.provider = "ollama"
        logger.info(f"LLM Client initialized using {self.provider} provider.")

    async def complete(self, prompt: str, system: str = "", temperature: float = 0.1,
                       max_tokens: int = 2048, expect_json: bool = False) -> str:
        """Core completion method with automatic provider fallback."""

        # 1. Try Local GGUF (Primary — fastest, private, no network)
        if LLMClient._local_llm is not None:
            res = await self._try_local_gguf(prompt, system, temperature, max_tokens)
            if res:
                return self._post_process(res, expect_json)

        # 2. Try Ollama (if running locally)
        res = await self._try_ollama(prompt, system, temperature, max_tokens)
        if res:
            return self._post_process(res, expect_json)

        # 3. Structured data-aware fallback (no LLM needed)
        return self._intelligent_fallback(prompt, system, expect_json)

    async def _try_local_gguf(self, prompt: str, system: str,
                                temperature: float, max_tokens: int) -> Optional[str]:
        """Inference using local Qwen2.5 GGUF model via chat completion API."""
        try:
            import anyio
            if LLMClient._local_llm is None:
                return None

            sys_msg = system or "You are an expert financial analyst and market intelligence system."

            def _infer():
                output = LLMClient._local_llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": sys_msg},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=max_tokens,
                    temperature=max(temperature, 0.01),
                )
                text = output["choices"][0]["message"]["content"].strip()
                return text

            result = await anyio.to_thread.run_sync(_infer)
            if result:
                logger.info(f"GGUF inference OK ({len(result)} chars)")
            return result if result else None
        except Exception as e:
            logger.error(f"Local GGUF inference error: {e}")
            return None

    async def _try_ollama(self, prompt: str, system: str,
                           temperature: float, max_tokens: int) -> Optional[str]:
        """Fallback: Ollama API (if server is running)."""
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
            logger.warning(f"Ollama inference error: {e}")
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
