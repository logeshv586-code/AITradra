import sqlite3
import json
import os
from datetime import datetime, timedelta
from core.logger import get_logger

logger = get_logger(__name__)

class SmartCache:
    """
    SQLite-backed cache with TTL and source tracking.
    Never deletes old data — marks it stale instead.
    """

    def __init__(self, db_path="market_data.sqlite3"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT,
                    data_type TEXT,
                    value TEXT,
                    source TEXT,
                    timestamp DATETIME,
                    PRIMARY KEY (key, data_type)
                )
            """)

    def get(self, key: str, data_type: str) -> tuple[dict | None, bool]:
        """Returns (data, is_fresh). data is None only if never cached."""
        from gateway.config import Config
        
        ttl_minutes = Config.CACHE_TTL.get(data_type, 15)
        # Convert hours to minutes if needed (based on implementation prompt TTL keys)
        if data_type in ["sentiment", "fundamentals", "analysis"]:
            ttl_minutes *= 60

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT value, timestamp FROM cache WHERE key = ? AND data_type = ?",
                (key, data_type)
            )
            row = cursor.fetchone()
            
            if not row:
                return None, False
            
            value_json, ts_str = row
            data = json.loads(value_json)
            ts = datetime.fromisoformat(ts_str)
            
            is_fresh = datetime.now() - ts < timedelta(minutes=ttl_minutes)
            return data, is_fresh

    def set(self, key: str, data_type: str, value: dict, source: str):
        """Store with timestamp and source name."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cache (key, data_type, value, source, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (key, data_type, json.dumps(value), source, datetime.now().isoformat()))

    def get_freshness_label(self, key: str, data_type: str) -> str:
        """Returns 'Live', 'Cached 4h ago', 'Estimated', or 'Stale'."""
        data, is_fresh = self.get(key, data_type)
        if not data:
            return "No Data"
        
        if is_fresh:
            return "Live"
        
        # Calculate how long ago
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT timestamp, source FROM cache WHERE key = ? AND data_type = ?",
                (key, data_type)
            )
            row = cursor.fetchone()
            if row:
                ts_str, source = row
                ts = datetime.fromisoformat(ts_str)
                diff = datetime.now() - ts
                
                if diff.total_seconds() < 3600:
                    return f"Cached {int(diff.total_seconds()/60)}m ago"
                elif diff.days < 1:
                    return f"Cached {int(diff.total_seconds()/3600)}h ago"
                else:
                    return "Stale"
        
        return "Unknown"

# Global instance
cache = SmartCache()
