import os

filepath = r"c:\Users\e629\Desktop\AITradra\llm\client.py"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update __init__
init_old = """        # Determine provider
        if settings.LLM_PROVIDER == "nvidia_nim":
            self.provider = "nvidia_nim"
        elif LLMClient._local_reasoning_llm is not None or LLMClient._local_general_llm is not None:
            self.provider = "local_gguf"
        else:
            self.provider = "ollama\""""

init_new = """        # Determine provider
        if settings.USE_LM_STUDIO:
            self.provider = "lm_studio"
        elif settings.LLM_PROVIDER == "nvidia_nim":
            self.provider = "nvidia_nim"
        elif LLMClient._local_reasoning_llm is not None or LLMClient._local_general_llm is not None:
            self.provider = "local_gguf"
        else:
            self.provider = "ollama\""""

# Using a simpler find/replace to avoid multi-line exact match issues with \r\n
content = content.replace('if settings.LLM_PROVIDER == "nvidia_nim":', 'if settings.USE_LM_STUDIO:\n            self.provider = "lm_studio"\n        elif settings.LLM_PROVIDER == "nvidia_nim":')

# 2. Update complete method
content = content.replace('"""Core completion method with NIM -> Local -> Ollama fallback."""', 
                          '"""Core completion method with LM Studio -> NIM -> Local -> Ollama fallback."""')

complete_block_old = """        # 1. Try NVIDIA NIM (Primary)
        if self.provider == "nvidia_nim":
            content = await self._try_nvidia_nim(prompt, system, temperature, max_tokens, role)
            if content:
                return self._post_process(content, expect_json)
            logger.warning(f"NIM failed for role '{role}', falling back to local GGUF.")"""

complete_block_new = """        # 1. Try LM Studio (Priority if enabled)
        if self.provider == "lm_studio" or settings.USE_LM_STUDIO:
            content = await self._try_lm_studio(prompt, system, temperature, max_tokens)
            if content:
                return self._post_process(content, expect_json)
            logger.warning("LM Studio failed, falling back to other providers.")

        # 2. Try NVIDIA NIM (Primary)
        if self.provider == "nvidia_nim":
            content = await self._try_nvidia_nim(prompt, system, temperature, max_tokens, role)
            if content:
                return self._post_process(content, expect_json)
            logger.warning(f"NIM failed for role '{role}', falling back to local GGUF.")"""

# Replace the block
content = content.replace('# 1. Try NVIDIA NIM (Primary)', 
                          '# 1. Try LM Studio (Priority if enabled)\n        if self.provider == "lm_studio" or settings.USE_LM_STUDIO:\n            content = await self._try_lm_studio(prompt, system, temperature, max_tokens)\n            if content:\n                return self._post_process(content, expect_json)\n            logger.warning("LM Studio failed, falling back to other providers.")\n\n        # 2. Try NVIDIA NIM (Primary)')

# 3. Add _try_lm_studio method
try_lm_studio_method = """
    async def _try_lm_studio(self, prompt: str, system: str,
                             temperature: Optional[float], max_tokens: Optional[int]) -> Optional[str]:
        \"\"\"Inference using LM Studio's OpenAI-compatible API.\"\"\"
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

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{settings.LM_STUDIO_URL}/chat/completions",
                    headers=headers, json=payload
                )
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                
                logger.error(f"LM Studio error: {response.status_code} - {response.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"LM Studio connection failed: {e}")
            return None
"""

if '_try_lm_studio' not in content:
    # Insert before _try_nvidia_nim
    content = content.replace('async def _try_nvidia_nim', try_lm_studio_method + '\n    async def _try_nvidia_nim')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied successfully.")
