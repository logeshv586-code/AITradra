import sqlite3
import os

def full_diag():
    db_path = "axiom_knowledge.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Tables in DB ---")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for table in tables:
        t_name = table[0]
        print(f"\nTable: {t_name}")
        cursor.execute(f"PRAGMA table_info({t_name})")
        cols = cursor.fetchall()
        for col in cols:
            print(f"  Col: {col[1]} ({col[2]})")
        
        cursor.execute(f"SELECT COUNT(*) FROM {t_name}")
        count = cursor.fetchone()[0]
        print(f"  Total Records: {count}")
        
    print("\n--- Current Watchlist from settings (if possible) ---")
    try:
        from core.config import settings
        print(f"Watchlist: {settings.DEFAULT_WATCHLIST}")
    except Exception as e:
        print(f"Could not load settings: {e}")

    conn.close()

if __name__ == "__main__":
    full_diag()
