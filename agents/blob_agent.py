import os
import json
from datetime import datetime

class BlobAgent:
    """Agent 2: Blob Storage Agent - Persists market intelligence."""
    
    def __init__(self, base_path="gateway/market_blob"):
        self.name = "BlobStorageAgent"
        self.base_path = base_path
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)

    def save_blob(self, data: dict):
        symbol = data.get("symbol")
        if not symbol:
            return False
            
        symbol_path = os.path.join(self.base_path, symbol)
        if not os.path.exists(symbol_path):
            os.makedirs(symbol_path)
            
        date_str = datetime.now().strftime("%Y-%m-%d")
        file_path = os.path.join(symbol_path, f"{date_str}.json")
        
        print(f"[{self.name}] Saving blob for {symbol} to {file_path}")
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        return file_path

    def load_blob(self, symbol: str, date_str: str = None):
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
            
        file_path = os.path.join(self.base_path, symbol, f"{date_str}.json")
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return json.load(f)
        return None

    def get_stock_history(self, symbol: str, limit: int = 7):
        symbol_path = os.path.join(self.base_path, symbol)
        if not os.path.exists(symbol_path):
            return []
            
        files = sorted([f for f in os.listdir(symbol_path) if f.endswith(".json")], reverse=True)
        history = []
        for f in files[:limit]:
            with open(os.path.join(symbol_path, f), "r") as ff:
                history.append(json.load(ff))
        return history

    def cleanup_old_data(self, symbol: str, days_to_keep: int = 7):
        # Implementation for cleaning up old blobs
        pass

if __name__ == "__main__":
    agent = BlobAgent()
    test_data = {"symbol": "AAPL", "price": 190.22, "timestamp": datetime.now().isoformat()}
    path = agent.save_blob(test_data)
    print(f"Saved to {path}")
    print(f"History: {len(agent.get_stock_history('AAPL'))} items")
