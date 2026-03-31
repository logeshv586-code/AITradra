from agents.sentiment_classifier import SentimentClassifierAgent
try:
    a = SentimentClassifierAgent()
    print("Successfully instantiated SentimentClassifierAgent")
except TypeError as e:
    print(f"FAILED: {e}")
except Exception as e:
    print(f"ERROR: {e}")
