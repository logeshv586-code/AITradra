import os
from core.logger import get_logger

logger = get_logger(__name__)

class MistralGGUFProvider:
    """Local inference provider using llama-cpp-python and a GGUF model."""
    
    def __init__(self, model_path: str):
        self.model_path = model_path
        self._llm = None
        self._initialize_model()

    def _initialize_model(self):
        try:
            from llama_cpp import Llama
            logger.info("Initializing Mistral GGUF model via llama-cpp-python...")
            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=4096,   # Context window size
                n_threads=4,  # Adjust based on CPU cores
                verbose=False # Set to True for detailed C++ logs
            )
            logger.info("Mistral model loaded successfully.")
        except ImportError:
            logger.error("llama-cpp-python is not installed. Run `pip install llama-cpp-python`.")
        except Exception as e:
            logger.error(f"Failed to load Mistral model: {e}")

    def generate(self, prompt: str, system: str = "", temperature: float = 0.1, max_tokens: int = 1000) -> str:
        """Generate response synchronously."""
        if not self._llm:
            raise RuntimeError("Mistral model is not initialized.")

        try:
            response = self._llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            content = response["choices"][0]["message"]["content"]
            return content.strip() if content else ""
        except Exception as e:
            logger.error(f"Mistral/Nemotron inference failed: {e}")
            raise
