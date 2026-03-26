import os
from llama_cpp import Llama

def test_mistral_model():
    model_path = os.path.join(os.path.dirname(__file__), "..", "mistral-7b-instruct-v0.2.Q4_K_S.gguf")
    
    print(f"Loading model from: {os.path.abspath(model_path)}")
    
    if not os.path.exists(model_path):
        print(f"Error: Model not found at {model_path}")
        return

    # Initialize the model
    print("Initializing llama-cpp-python...")
    llm = Llama(
        model_path=model_path,
        n_ctx=2048,   # Context window size
        n_threads=4,  # Adjust based on CPU cores
        verbose=False # Set to True for detailed C++ logs
    )

    prompt = """[INST] You are an AI Trading Assistant. Analyze whether MSFT is a good buy. Provide a 2 sentence summary. [/INST]
MSFT looks like a good buy because"""

    print("\nRunning inference...")
    print(f"Prompt: {prompt}\n")
    
    response = llm(
        prompt,
        max_tokens=100,
        temperature=0.7,
        stop=["[/INST]", "USER:"],
        echo=False
    )
    
    output = response["choices"][0]["text"].strip()
    print(f"--- MODEL OUTPUT ---\n{output}\n--------------------")

if __name__ == "__main__":
    test_mistral_model()
