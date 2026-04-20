import sqlite3
import os
import sys

# Add current dir to path
sys.path.append(os.getcwd())

from core.config import settings
from gateway.knowledge_store import knowledge_store

def verify():
    print(f"Checking DB: {settings.KNOWLEDGE_DB_PATH}")
    conn = sqlite3.connect(settings.KNOWLEDGE_DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Check table info
    cursor = conn.execute("PRAGMA table_info(daily_ohlcv)")
    cols = [row[1] for row in cursor.fetchall()]
    print(f"Columns in daily_ohlcv: {cols}")
    
    if "market_cap" in cols and "pe_ratio" in cols:
        print("✅ Columns exist.")
    else:
        print("❌ Columns missing!")
        return

    # Check for records with data
    row = conn.execute("SELECT ticker, market_cap, pe_ratio FROM daily_ohlcv WHERE market_cap > 0 LIMIT 5").fetchone()
    if row:
        print(f"✅ Found fundamentals for {row['ticker']}: MCAP={row['market_cap']}, PE={row['pe_ratio']}")
    else:
        print("⚠️ No fundamentals found yet (waiting for collector background task).")

if __name__ == "__main__":
    verify()
