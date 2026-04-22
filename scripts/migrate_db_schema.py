import sqlite3
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = 'axiom_knowledge.db'

def migrate_schema():
    if not os.path.exists(DB_PATH):
        logger.error(f"Database {DB_PATH} not found. Nothing to migrate.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check current columns in agent_insights
        cursor.execute("PRAGMA table_info(agent_insights)")
        cols = {row[1] for row in cursor.fetchall()}
        
        logger.info(f"Current columns in agent_insights: {cols}")

        migrated = False

        # 1. Migrate 'symbol' to 'ticker'
        if 'symbol' in cols and 'ticker' not in cols:
            logger.info("Migrating 'symbol' column to 'ticker'...")
            cursor.execute("ALTER TABLE agent_insights RENAME COLUMN symbol TO ticker")
            migrated = True
        elif 'symbol' in cols and 'ticker' in cols:
            logger.info("'ticker' already exists. Copying data from 'symbol' if null...")
            cursor.execute("UPDATE agent_insights SET ticker = symbol WHERE ticker IS NULL OR ticker = ''")
            migrated = True

        # 2. Migrate 'payload' to 'content'
        if 'payload' in cols and 'content' not in cols:
            logger.info("Migrating 'payload' column to 'content'...")
            cursor.execute("ALTER TABLE agent_insights RENAME COLUMN payload TO content")
            migrated = True
        elif 'payload' in cols and 'content' in cols:
            logger.info("'content' already exists. Copying data from 'payload' if null...")
            cursor.execute("UPDATE agent_insights SET content = payload WHERE content IS NULL OR content = ''")
            migrated = True
            
        # 3. Add other missing columns from KnowledgeStore definition if they don't exist
        # Expected: id, ticker, agent_name, insight_type, content, confidence, source_urls, embedding_indexed, created_at
        expected_cols = {
            "insight_type": "TEXT",
            "confidence": "REAL DEFAULT 0.0",
            "source_urls": "TEXT",
            "embedding_indexed": "INTEGER DEFAULT 0",
            "created_at": "TEXT DEFAULT (datetime('now'))"
        }
        
        for col, dtype in expected_cols.items():
            if col not in cols and col.lower() not in cols: # case-insensitive check
                logger.info(f"Adding missing column '{col}'...")
                cursor.execute(f"ALTER TABLE agent_insights ADD COLUMN {col} {dtype}")
                migrated = True

        if migrated:
            conn.commit()
            logger.info("Migration successful.")
        else:
            logger.info("No migration needed for agent_insights.")

    except Exception as e:
        conn.rollback()
        logger.error(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_schema()
