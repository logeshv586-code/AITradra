import sqlite3
import os

def check_db():
    db_path = "axiom_knowledge.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Tickers in daily_ohlcv ---")
    cursor.execute("SELECT DISTINCT ticker FROM daily_ohlcv")
    rows = cursor.fetchall()
    for row in rows:
        print(f"Ticker: {row[0]}")
        
    print("\n--- Sample data for NFLX ---")
    cursor.execute("SELECT * FROM daily_ohlcv WHERE ticker = 'NFLX' LIMIT 1")
    row = cursor.fetchone()
    if row:
        print(f"NFLX Record: {row}")
    else:
        print("No records found for NFLX")
        
    print("\n--- Database Schema ---")
    cursor.execute("PRAGMA table_info(daily_ohlcv)")
    cols = cursor.fetchall()
    for col in cols:
        print(f"Col: {col[1]} ({col[2]})")

    conn.close()

if __name__ == "__main__":
    check_db()
