"""
UNIVERSAL TICKER REGISTRY (100% OSS)
Maps global assets securely using strictly free/open-source APIs.
Supports: Equities (yfinance/stooq), Crypto (ccxt), Forex (stooq), Commodities (stooq).
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional

class AssetClass(str, Enum):
    EQUITY = "equity"
    CRYPTO = "crypto"
    FOREX = "forex"
    COMMODITY = "commodity"
    ETF = "etf"
    INDEX = "index"

class Exchange(str, Enum):
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    LSE = "LSE"
    TSE = "TSE"
    HKEX = "HKEX"
    NSE = "NSE"
    BINANCE = "BINANCE"
    BYBIT = "BYBIT"
    OKX = "OKX"
    GLOBAL_FX = "GLOBAL_FX"

@dataclass
class UniversalAsset:
    ticker: str                    
    name: str
    asset_class: AssetClass
    exchange: Exchange
    data_source: str               # "yfinance" | "stooq" | "ccxt" | "coinpaprika" | "alphavantage"
    currency: str                  
    is_24_7: bool                  

GLOBAL_UNIVERSE = {
    # US EQUITIES
    "AAPL":  UniversalAsset("AAPL", "Apple Inc", AssetClass.EQUITY, Exchange.NASDAQ, "yfinance", "USD", False),
    "MSFT":  UniversalAsset("MSFT", "Microsoft", AssetClass.EQUITY, Exchange.NASDAQ, "yfinance", "USD", False),
    
    # GLOBAL EQUITIES
    "RELIANCE": UniversalAsset("RELIANCE", "Reliance Ind", AssetClass.EQUITY, Exchange.NSE, "yfinance", "INR", False),
    "TOYOTA": UniversalAsset("TOYOTA", "Toyota", AssetClass.EQUITY, Exchange.TSE, "yfinance", "JPY", False),

    # CRYPTO (CCXT)
    "BTC": UniversalAsset("BTC", "Bitcoin", AssetClass.CRYPTO, Exchange.BINANCE, "ccxt", "USD", True),
    "ETH": UniversalAsset("ETH", "Ethereum", AssetClass.CRYPTO, Exchange.BINANCE, "ccxt", "USD", True),
    "SOL": UniversalAsset("SOL", "Solana", AssetClass.CRYPTO, Exchange.BINANCE, "ccxt", "USD", True),

    # FOREX & COMMODITIES
    "EURUSD": UniversalAsset("EURUSD", "EUR/USD", AssetClass.FOREX, Exchange.GLOBAL_FX, "stooq", "USD", True),
    "GOLD": UniversalAsset("GOLD", "Gold Futures", AssetClass.COMMODITY, Exchange.NYSE, "yfinance", "USD", False),
}

class TickerRegistry:
    def __init__(self):
        self.universe = GLOBAL_UNIVERSE

    def resolve(self, ticker: str) -> Optional[UniversalAsset]:
        upper = ticker.upper()
        if upper in self.universe:
            return self.universe[upper]

        if "USDT" in ticker or ticker in ["BTC", "ETH", "SOL", "XRP", "DOGE"]:
            return UniversalAsset(ticker, ticker, AssetClass.CRYPTO, Exchange.BINANCE, "ccxt", "USD", True)
        if "/" in ticker:
            return UniversalAsset(ticker, ticker, AssetClass.FOREX, Exchange.GLOBAL_FX, "stooq", "USD", True)
            
        # Default fallback to Yfinance OSS equity
        return UniversalAsset(ticker, ticker, AssetClass.EQUITY, Exchange.NASDAQ, "yfinance", "USD", False)
