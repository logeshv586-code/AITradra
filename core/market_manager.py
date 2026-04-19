import datetime
from typing import Dict, List, Optional

class MarketManager:
    """Manages global market timings in IST (India Standard Time)."""
    
    # Timing format: (start_hour, start_minute, end_hour, end_minute)
    # Note: US Market crosses midnight (19:00 - 01:30)
    MARKETS = {
        "JAPAN": {"name": "Japan (Tokyo)", "start": (5, 30), "end": (11, 30), "emoji": "🇯🇵"},
        "CHINA": {"name": "China (Shanghai)", "start": (7, 0), "end": (12, 30), "emoji": "🇨🇳"},
        "HONG_KONG": {"name": "Hong Kong", "start": (6, 45), "end": (13, 30), "emoji": "🇭🇰"},
        "INDIA": {"name": "India (NSE/BSE)", "start": (9, 15), "end": (15, 30), "emoji": "🇮🇳"},
        "EUROPE": {"name": "Europe (London/Euronext)", "start": (13, 30), "end": (22, 0), "emoji": "🇪🇺"},
        "US": {"name": "US (NYSE/NASDAQ)", "start": (19, 0), "end": (1, 30), "emoji": "🇺🇸"},
        "CRYPTO": {"name": "Cryptocurrency", "start": (0, 0), "end": (23, 59), "emoji": "🪙"},
    }

    @staticmethod
    def get_ist_now() -> datetime.datetime:
        """Returns the current time in IST."""
        # Using the system local time as it is already +05:30 based on metadata
        return datetime.datetime.now()

    @classmethod
    def get_market_status(cls, market_key: str) -> str:
        """Returns 'OPEN' or 'CLOSED' for a given market key."""
        if market_key not in cls.MARKETS:
            return "UNKNOWN"
            
        market = cls.MARKETS[market_key]
        now = cls.get_ist_now()
        current_time = now.time()
        
        start_time = datetime.time(int(market["start"][0]), int(market["start"][1]))
        end_time = datetime.time(int(market["end"][0]), int(market["end"][1]))
        
        # Handle overnight markets (like US: 19:00 - 01:30)
        if start_time > end_time:
            if current_time >= start_time or current_time <= end_time:
                return "OPEN"
        else:
            if start_time <= current_time <= end_time:
                return "OPEN"
                
        return "CLOSED"

    @classmethod
    def get_all_statuses(cls) -> Dict[str, Dict]:
        """Returns the current status of all major markets."""
        statuses = {}
        for key, info in cls.MARKETS.items():
            statuses[key] = {
                "name": info["name"],
                "status": cls.get_market_status(key),
                "emoji": info["emoji"]
            }
        return statuses

    @classmethod
    def get_market_for_ticker(cls, ticker: str) -> str:
        """Maps a ticker symbol to its primary market."""
        ticker = ticker.upper()
        if ticker.endswith(".NS") or ticker.endswith(".BO"):
            return "INDIA"
        if ticker.endswith(".T"):
            return "JAPAN"
        if ticker.endswith(".HK"):
            return "HONG_KONG"
        if ticker.endswith(".SS") or ticker.endswith(".SZ"):
            return "CHINA"
        if ticker.endswith(".L") or ticker.endswith(".DE") or ticker.endswith(".PA"):
            return "EUROPE"
            
        if ticker.endswith("-USD"):
            return "CRYPTO"
            
        # Default to US for major tech/growth stocks or no suffix
        return "US"

    @classmethod
    def get_ai_suggestion_context(cls, ticker: str) -> str:
        """Returns context for AI suggestions based on market status."""
        market_key = cls.get_market_for_ticker(ticker)
        status = cls.get_market_status(market_key)
        market_name = cls.MARKETS[market_key]["name"]
        
        if status == "OPEN":
            return f"The {market_name} is currently LIVE. Focus on real-time trade opportunities and immediate momentum."
        else:
            return f"The {market_name} is currently CLOSED. Focus on next-session predictions, gap-up/down analysis, and post-market news reaction."

if __name__ == "__main__":
    print("AXIOM Market Manager Status:")
    for m, s in MarketManager.get_all_statuses().items():
        print(f"{s['emoji']} {s['name']}: {s['status']}")
