import sqlite3
import os

db_path = "data/axiom_knowledge.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(agent_episodes)")
        columns = cursor.fetchall()
        print(f"Columns in agent_episodes: {[c[1] for c in columns]}")
    except Exception as e:
        print(f"Error checking agent_episodes: {e}")
    conn.close()
else:
    print(f"DB not found at {db_path}")
