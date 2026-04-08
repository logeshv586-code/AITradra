"""
Indicator Service — Computes technical indicators for market analysis.
Uses pandas-ta for robust technical evaluation.
"""

import pandas as pd
import pandas_ta as ta
from typing import Optional, Dict

class IndicatorService:
    """
    Computes EMA, RSI, MACD, ATR, BBands, ADX, OBV, and VWAP.
    Matches the requirements of the Hyperliquid Trading Agent.
    """
    
    @staticmethod
    def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Expects a DataFrame with [timestamp, open, high, low, close, volume].
        Returns a DataFrame with technical indicators added.
        """
        if df.empty:
            return df
        
        # Ensure correct types
        cols = ['open', 'high', 'low', 'close', 'volume']
        for col in cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # EMA (12 and 26)
        df['EMA_12'] = ta.ema(df['close'], length=12)
        df['EMA_26'] = ta.ema(df['close'], length=26)
        
        # RSI (14)
        df['RSI_14'] = ta.rsi(df['close'], length=14)
        
        # MACD
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        if macd is not None:
            df = pd.concat([df, macd], axis=1)
        
        # ATR (14)
        df['ATR_14'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        # Bollinger Bands
        bbands = ta.bbands(df['close'], length=20, std=2)
        if bbands is not None:
            df = pd.concat([df, bbands], axis=1)
            
        # ADX (14)
        adx = ta.adx(df['high'], df['low'], df['close'], length=14)
        if adx is not None:
            df = pd.concat([df, adx], axis=1)
            
        # OBV
        df['OBV'] = ta.obv(df['close'], df['volume'])
        
        # VWAP
        # Note: VWAP usually needs an HLC3 column
        df['VWAP'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
        
        return df

    @staticmethod
    def get_latest_indicators(df: pd.DataFrame) -> Dict[str, any]:
        """Returns the latest indicator values as a dictionary."""
        df = IndicatorService.compute_indicators(df)
        if df.empty:
            return {}
        
        latest = df.iloc[-1].to_dict()
        # Clean up NaN values for JSON serialization
        return {k: (v if pd.notnull(v) else None) for k, v in latest.items()}
