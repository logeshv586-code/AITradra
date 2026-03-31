import sqlite3
import zlib
import json
import os
from datetime import datetime, timezone
from core.logger import get_logger

logger = get_logger(__name__)


class CompressedDataStore:
    """Stores massive datasets in SQLite via zlib compressed BLOBs for tiny footprints."""

    def __init__(self, db_path=None):
        if db_path is None:
            self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "market_data.sqlite3")
        else:
            self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS market_blobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    data_type TEXT NOT NULL,
                    compressed_payload BLOB NOT NULL
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_ticker ON market_blobs(ticker)')
            
    def _encode_payload(self, data: dict | list) -> bytes:
        """Serializes to JSON and encodes via zlib compression."""
        json_str = json.dumps(data)
        return zlib.compress(json_str.encode('utf-8'), level=9)

    def _decode_payload(self, compressed_bytes: bytes) -> dict | list:
        """Decompresses zlib BLOB back into Python objects."""
        decompressed_str = zlib.decompress(compressed_bytes).decode('utf-8')
        return json.loads(decompressed_str)

    def save_live_data(self, ticker: str, data_type: str, data: dict | list):
        """Saves highly compressed data payload into the historical sync."""
        payload = self._encode_payload(data)
        now = datetime.now(timezone.utc).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO market_blobs (ticker, timestamp, data_type, compressed_payload) VALUES (?, ?, ?, ?)",
                (ticker, now, data_type, payload)
            )
        logger.info(f"Saved highly-compressed {data_type} data for {ticker} (Size: {len(payload)} bytes)")

    def get_latest_data(self, ticker: str, data_type: str) -> dict | list | None:
        """Retrieves and decompresses the latest data payload."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT compressed_payload FROM market_blobs WHERE ticker=? AND data_type=? ORDER BY timestamp DESC LIMIT 1",
                (ticker, data_type)
            )
            row = cursor.fetchone()
            if row:
                return self._decode_payload(row[0])
            return None
