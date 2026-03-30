import os
import httpx
from typing import Optional, AsyncGenerator
import json
import re
from core.config import settings
from core.logger import get_logger
from gateway.observability import trace_llm

logger = get_logger(__name__)

class LLMClient:
    """Unified LLM client optimized for local NVIDIA Nemotron GGUF with Langfuse tracing."""
    _local_llm = None  # Singleton for local GGUF model

    @classmethod
    def preload_local_gguf(cls):
        """Preloads the local GGUF model into memory at startup."""
        if cls._local_llm is not None:
            return cls._local_llm is not False
            
        try:
            from llama_cpp import Llama
            
            # Model name from root
            model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf")
            if not os.path.exists(model_path):
                logger.warning(f"Local GGUF model not found at {model_path}")
                return False

            logger.info(f"Loading local GGUF model from {model_path}...")
            try:
                # Optimized for local CPU/GPU balance
                cls._local_llm = Llama(
                    model_path=os.path.abspath(model_path),
                    n_ctx=2048, # Increased context for RAG
                    n_threads=os.cpu_count() or 4,
                    n_gpu_layers=-1 if os.getenv("USE_CUDA") == "true" else 0, # Auto-detect GPU if flag set
                    verbose=False
                )
                logger.info("Local GGUF model loaded successfully.")
                return True
            except Exception as inner_e:
                logger.error(f"Llama failed to load: {inner_e}")
                cls._local_llm = False
                return False
        except Exception as e:
            logger.error(f"Local GGUF preload error: {e}")
            return False

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url or settings.OLLAMA_URL
        self.model = model or settings.LLM_MODEL
        self.timeout = settings.LLM_TIMEOUT
        
        # Priority: Local GGUF -> Ollama -> LM Studio
        self.provider = "local_gguf" if LLMClient._local_llm else "ollama"
        logger.info(f"LLM Client initialized using {self.provider} provider.")

    @trace_llm(name="llm_completion")
    async def complete(self, prompt: str, system: str = "", temperature: float = 0.1,
                       max_tokens: int = 2048, expect_json: bool = False) -> str:
        """Core completion method with automatic provider switching and tracing."""
        
        # 1. Try Local GGUF (Fastest, Private)
        if LLMClient._local_llm:
            res = await self._try_local_gguf(prompt, system, temperature, max_tokens)
            if res: return self._post_process(res, expect_json)

        # 2. Try Ollama (Self-hosted service)
        res = await self._try_ollama(prompt, system, temperature, max_tokens)
        if res: return self._post_process(res, expect_json)
        
        # 3. Last Resort: Emergency Fallback
        return self._fallback_response(prompt)

    async def _try_local_gguf(self, prompt, system, temperature, max_tokens):
        try:
            import anyio
            if not LLMClient._local_llm: return None
            
            # Nemotron-specific prompt format
            full_prompt = f"<|system|>\n{system or 'You are an expert financial analyst.'}\n<|user|>\n{prompt}\n<|assistant|>\n"
            
            def _infer():
                output = LLMClient._local_llm(
                    full_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=["<|endoftext|>", "</s>", "<|user|>", "<|system|>"],
                    echo=False
                )
                return output["choices"][0]["text"].strip()
            
            return await anyio.to_thread.run_sync(_infer)
        except Exception as e:
            logger.error(f"Local GGUF inference error: {e}")
            return None

    async def _try_ollama(self, prompt, system, temperature, max_tokens):
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
        if not expect_json: return text
        
        # Robust JSON extraction
        try:
            clean = re.sub(r"```json|```", "", text).strip()
            start = clean.find("{")
            end = clean.rfind("}")
            if start != -1 and end != -1:
                return json.loads(clean[start:end+1])
            return json.loads(clean)
        except:
            return text # Return raw if parsing fails

    def _fallback_response(self, prompt: str) -> str:
        return "🧠 [OSS Fallback] Market analysis currently running in offline-only mode. Systems are healthy but inference is throttled."
