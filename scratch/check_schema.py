import sqlite3
import os

DB_PATH = 'axiom_knowledge.db'

def check_schema(table_name):
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found")
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print(f"Schema for {table_name}:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
    except Exception as e:
        print(f"Error checking {table_name}: {e}")
    finally:
        conn.close()

tables = ['agent_insights', 'news_articles', 'daily_ohlcv', 'rag_index_log']
for t in tables:
    check_schema(t)
    print("-" * 20)
