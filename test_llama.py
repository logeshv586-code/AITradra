from llama_cpp import Llama
import sys
try:
    print("Loading model...")
    llm = Llama(model_path="NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf", n_ctx=512, n_threads=4, n_gpu_layers=0, verbose=True)
    print("Success")
except Exception as e:
    print("FAIL:", e)
