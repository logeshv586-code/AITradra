import sqlite3
import os

db_path = "data/axiom_knowledge.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Check all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Tables: {[t[0] for t in tables]}")
        
        for table in [t[0] for t in tables]:
            cursor.execute(f"PRAGMA table_info({table})")
            cols = cursor.fetchall()
            print(f"Cols for {table}: {[c[1] for c in cols]}")
            
    except Exception as e:
        print(f"Error: {e}")
    conn.close()
else:
    print(f"DB not found")
