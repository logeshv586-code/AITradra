import sqlite3
import os

def full_diag():
    # Corrected path based on settings.KNOWLEDGE_DB_PATH
    db_path = "data/axiom_knowledge.db"
    
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    print(f"Inspecting active database: {db_path}\n")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tables = ["daily_ohlcv", "news_articles", "agent_health"]
    for t_name in tables:
        print(f"--- Table: {t_name} ---")
        cursor.execute(f"PRAGMA table_info({t_name})")
        cols = [row[1] for row in cursor.fetchall()]
        print(f"Columns: {cols}")
        
        cursor.execute(f"SELECT COUNT(*) FROM {t_name}")
        count = cursor.fetchone()[0]
        print(f"Total Records: {count}")
        
        if count > 0:
            print("Sample Record:")
            cursor.execute(f"SELECT * FROM {t_name} LIMIT 1")
            print(cursor.fetchone())
        print("-" * 30)

    # Specific check for NFLX
    print("\n--- NFLX Specific Data ---")
    cursor.execute("SELECT COUNT(*) FROM daily_ohlcv WHERE ticker = 'NFLX'")
    print(f"NFLX OHLCV Records: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM news_articles WHERE ticker = 'NFLX'")
    print(f"NFLX News Records: {cursor.fetchone()[0]}")

    conn.close()

if __name__ == "__main__":
    full_diag()
