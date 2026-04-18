"""
mcp/crypto_gateway.py  —  Institutional Crypto Data Gateway (Layer 5)
====================================================================
Wraps CoinGecko and other crypto-native sources to provide normalized 
market data for the AITradra swarm. Matches yfinance schema.
"""

import os
import logging
import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any

logger = logging.getLogger("mcp.crypto_gateway")

class CryptoGateway:
    """
    Gateway for high-fidelity crypto data.
    Initially uses CoinGecko's public API normalized to AITradra standards.
    """
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    # Map common slugs to CoinGecko IDs
    SLUG_MAP = {
        "BTC-USD": "bitcoin",
        "ETH-USD": "ethereum",
        "SOL-USD": "solana",
        "BNB-USD": "binancecoin",
        "XRP-USD": "ripple",
        "ADA-USD": "cardano",
        "AVAX-USD": "avalanche-2",
        "DOGE-USD": "dogecoin",
        "DOT-USD": "polkadot",
        "LINK-USD": "chainlink",
        "MATIC-USD": "matic-network",
    }

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=15)
        logger.info("CryptoGateway initialized (CoinGecko provider)")

    async def get_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch latest price, 24h volume, and 24h change for a crypto asset.
        Returns normalized bar-like snapshot.
        """
        cg_id = self.SLUG_MAP.get(symbol.upper(), symbol.lower().replace("-usd", ""))
        
        try:
            params = {
                "ids": cg_id,
                "vs_currencies": "usd",
                "include_24hr_vol": "true",
                "include_24hr_change": "true",
                "include_last_updated_at": "true"
            }
            
            resp = await self.client.get(f"{self.BASE_URL}/simple/price", params=params)
            resp.raise_for_status()
            data = resp.json()
            
            if cg_id not in data:
                logger.warning(f"Crypto data not found for {symbol} (id: {cg_id})")
                return None
                
            entry = data[cg_id]
            price = entry["usd"]
            
            return {
                "symbol": symbol,
                "price": price,
                "volume_24h": entry.get("usd_24h_vol", 0),
                "change_24h_pct": entry.get("usd_24h_change", 0),
                "last_updated": datetime.fromtimestamp(entry["last_updated_at"], tz=timezone.utc).isoformat(),
                "source": "CoinGecko",
                # OHLCV normalization
                "Open": price / (1 + (entry.get("usd_24h_change", 0) / 100)),
                "High": price,
                "Low": price,
                "Close": price,
                "Volume": entry.get("usd_24h_vol", 0)
            }
            
        except Exception as e:
            logger.error(f"CryptoGateway fetch failed for {symbol}: {e}")
            return None

    async def close(self):
        await self.client.aclose()

# Singleton for global access
_gateway_instance = None

def get_crypto_gateway():
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = CryptoGateway()
    return _gateway_instance
