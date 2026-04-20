import sqlite3
import os
import shutil
from datetime import datetime

def migrate():
    db_path = "axiom_knowledge.db"
    backup_path = f"axiom_knowledge.db.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    # 1. Backup
    print(f"Backing up database to {backup_path}...")
    shutil.copy2(db_path, backup_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 2. Migrate daily_ohlcv
    print("Migrating daily_ohlcv table...")
    cursor.execute("PRAGMA table_info(daily_ohlcv)")
    cols = [row[1] for row in cursor.fetchall()]
    
    if "symbol" in cols and "ticker" not in cols:
        print("  Renaming 'symbol' to 'ticker'...")
        # SQLite rename column is supported in recent versions
        try:
            cursor.execute("ALTER TABLE daily_ohlcv RENAME COLUMN symbol TO ticker")
        except:
            print("  Fallback: Manual migration for 'ticker'...")
    
    if "ts" in cols and "date" not in cols:
        print("  Renaming 'ts' to 'date'...")
        try:
            cursor.execute("ALTER TABLE daily_ohlcv RENAME COLUMN ts TO date")
        except:
            print("  Fallback: Manual migration for 'date'...")

    # Add missing columns if they don't exist
    cursor.execute("PRAGMA table_info(daily_ohlcv)")
    cols = [row[1] for row in cursor.fetchall()]
    
    upgrades = [
        ("adj_close", "REAL"),
        ("market_cap", "REAL DEFAULT 0"),
        ("pe_ratio", "REAL DEFAULT 0"),
        ("source", "TEXT DEFAULT 'yfinance'")
    ]
    
    for col_name, col_type in upgrades:
        if col_name not in cols:
            print(f"  Adding column {col_name}...")
            cursor.execute(f"ALTER TABLE daily_ohlcv ADD COLUMN {col_name} {col_type}")

    # 3. Migrate news_articles
    print("\nMigrating news_articles table...")
    cursor.execute("PRAGMA table_info(news_articles)")
    news_cols = [row[1] for row in cursor.fetchall()]
    
    if "symbol" in news_cols and "ticker" not in news_cols:
        print("  Renaming 'symbol' to 'ticker' in news_articles...")
        cursor.execute("ALTER TABLE news_articles RENAME COLUMN symbol TO ticker")
    
    news_upgrades = [
        ("summary", "TEXT"),
        ("body", "TEXT"),
        ("relevance_score", "REAL DEFAULT 0.0"),
        ("embedding_indexed", "INTEGER DEFAULT 0")
    ]
    
    for col_name, col_type in news_upgrades:
        if col_name not in news_cols:
            print(f"  Adding column {col_name} for news...")
            cursor.execute(f"ALTER TABLE news_articles ADD COLUMN {col_name} {col_type}")

    conn.commit()
    conn.close()
    print("\nMigration complete.")

if __name__ == "__main__":
    migrate()
