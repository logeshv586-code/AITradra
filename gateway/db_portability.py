"""DB Portability — Export, import, and sync endpoints for axiom_knowledge.db.

Implements the DB portability strategies from the architecture diagram:
- SQL dump export/import (lightest, CI-friendly)
- REST sync API (HTTP push/pull)
- DB status and snapshot management
"""

import os
import subprocess
import sqlite3
import shutil
import json
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from core.logger import get_logger

logger = get_logger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "axiom_knowledge.db")
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db_backups")

router = APIRouter(prefix="/api/db", tags=["DB Portability"])


@router.get("/status")
async def db_status():
    """Get comprehensive DB status — size, table counts, last backup."""
    if not os.path.exists(DB_PATH):
        return {"error": "Database not found", "db_path": DB_PATH}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        # Table counts
        ohlcv_count = conn.execute("SELECT COUNT(*) FROM daily_ohlcv").fetchone()[0]
        news_count = conn.execute("SELECT COUNT(*) FROM news_articles").fetchone()[0]
        snapshot_count = conn.execute("SELECT COUNT(*) FROM market_snapshots").fetchone()[0]
        insight_count = conn.execute("SELECT COUNT(*) FROM agent_insights").fetchone()[0]

        # Distinct tickers
        tickers = conn.execute("SELECT COUNT(DISTINCT ticker) FROM daily_ohlcv").fetchone()[0]

        # Date ranges
        ohlcv_range = conn.execute(
            "SELECT MIN(date), MAX(date) FROM daily_ohlcv"
        ).fetchone()
        news_range = conn.execute(
            "SELECT MIN(created_at), MAX(created_at) FROM news_articles"
        ).fetchone()

        # DB file size
        db_size = os.path.getsize(DB_PATH)

        # Check for backups
        backups = []
        if os.path.exists(BACKUP_DIR):
            for f in sorted(os.listdir(BACKUP_DIR), reverse=True)[:5]:
                bp = os.path.join(BACKUP_DIR, f)
                backups.append({
                    "filename": f,
                    "size_mb": round(os.path.getsize(bp) / 1024 / 1024, 2),
                    "created": datetime.fromtimestamp(os.path.getctime(bp)).isoformat()
                })

        return {
            "db_path": DB_PATH,
            "db_size_bytes": db_size,
            "db_size_mb": round(db_size / 1024 / 1024, 2),
            "tables": {
                "daily_ohlcv": ohlcv_count,
                "news_articles": news_count,
                "market_snapshots": snapshot_count,
                "agent_insights": insight_count,
            },
            "tickers_with_ohlcv": tickers,
            "ohlcv_date_range": {
                "earliest": ohlcv_range[0] if ohlcv_range else None,
                "latest": ohlcv_range[1] if ohlcv_range else None,
            },
            "news_date_range": {
                "earliest": news_range[0] if news_range else None,
                "latest": news_range[1] if news_range else None,
            },
            "recent_backups": backups,
            "timestamp": datetime.now().isoformat(),
        }
    finally:
        conn.close()


@router.get("/export")
async def export_sql_dump():
    """Export axiom_knowledge.db as a SQL dump file.
    
    Strategy 2 from the portability hub — lightest, CI-friendly.
    The .sql file is plain text and can be committed to git.
    """
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail="Database not found")

    conn = sqlite3.connect(DB_PATH)
    try:
        # Generate SQL dump
        dump_lines = []
        for line in conn.iterdump():
            dump_lines.append(line)

        sql_content = "\n".join(dump_lines)

        # Stream as a downloadable file
        from io import BytesIO
        buffer = BytesIO(sql_content.encode("utf-8"))
        buffer.seek(0)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"axiom_knowledge_dump_{timestamp}.sql"

        return StreamingResponse(
            buffer,
            media_type="application/sql",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    finally:
        conn.close()


@router.post("/import")
async def import_sql_dump(file: UploadFile = File(...)):
    """Import a SQL dump to restore axiom_knowledge.db.
    
    WARNING: This will overwrite the existing database.
    Creates a backup before importing.
    """
    if not file.filename.endswith(".sql"):
        raise HTTPException(status_code=400, detail="File must be a .sql file")

    # Create backup first
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if os.path.exists(DB_PATH):
        backup_path = os.path.join(BACKUP_DIR, f"axiom_knowledge_pre_import_{timestamp}.db")
        shutil.copy2(DB_PATH, backup_path)
        logger.info(f"Pre-import backup created at {backup_path}")

    try:
        sql_content = await file.read()
        sql_text = sql_content.decode("utf-8")

        # Remove existing DB and create a fresh one
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

        conn = sqlite3.connect(DB_PATH)
        conn.executescript(sql_text)
        conn.commit()
        conn.close()

        logger.info(f"SQL dump imported successfully from {file.filename}")
        return {
            "status": "success",
            "message": f"Database restored from {file.filename}",
            "backup_created": f"axiom_knowledge_pre_import_{timestamp}.db",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"SQL import failed: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/snapshot")
async def create_snapshot():
    """Create a timestamped backup snapshot of axiom_knowledge.db.
    
    Useful before branch switches or system-to-system transfers.
    """
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail="Database not found")

    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_name = f"axiom_knowledge_snapshot_{timestamp}.db"
    snapshot_path = os.path.join(BACKUP_DIR, snapshot_name)

    shutil.copy2(DB_PATH, snapshot_path)
    size = os.path.getsize(snapshot_path)

    logger.info(f"DB snapshot created: {snapshot_name} ({size / 1024 / 1024:.2f} MB)")

    return {
        "status": "success",
        "snapshot": snapshot_name,
        "size_mb": round(size / 1024 / 1024, 2),
        "path": snapshot_path,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/sync/export")
async def sync_export():
    """REST sync export — returns the full DB state as JSON for system-to-system transfer.
    
    Strategy 4 from the portability hub — Sync REST API (HTTP push/pull).
    Lighter than full SQL dump for incremental syncs.
    """
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail="Database not found")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        data = {
            "daily_ohlcv": [dict(r) for r in conn.execute(
                "SELECT * FROM daily_ohlcv ORDER BY date DESC LIMIT 5000"
            ).fetchall()],
            "news_articles": [dict(r) for r in conn.execute(
                "SELECT * FROM news_articles ORDER BY created_at DESC LIMIT 1000"
            ).fetchall()],
            "agent_insights": [dict(r) for r in conn.execute(
                "SELECT * FROM agent_insights ORDER BY created_at DESC LIMIT 500"
            ).fetchall()],
            "export_timestamp": datetime.now().isoformat(),
            "record_counts": {
                "ohlcv": conn.execute("SELECT COUNT(*) FROM daily_ohlcv").fetchone()[0],
                "news": conn.execute("SELECT COUNT(*) FROM news_articles").fetchone()[0],
                "insights": conn.execute("SELECT COUNT(*) FROM agent_insights").fetchone()[0],
            }
        }

        return data
    finally:
        conn.close()


@router.post("/sync/import")
async def sync_import(data: dict):
    """REST sync import — receives JSON data and merges into axiom_knowledge.db.
    
    Uses INSERT OR IGNORE for idempotent merges.
    """
    from gateway.knowledge_store import knowledge_store

    results = {"ohlcv_inserted": 0, "news_inserted": 0, "insights_inserted": 0}

    # Import OHLCV
    ohlcv_records = data.get("daily_ohlcv", [])
    for record in ohlcv_records:
        ticker = record.get("ticker")
        if ticker:
            count = knowledge_store.store_daily_ohlcv(ticker, [record])
            results["ohlcv_inserted"] += count

    # Import news
    news_records = data.get("news_articles", [])
    results["news_inserted"] = knowledge_store.store_news(news_records)

    # Import insights
    for insight in data.get("agent_insights", []):
        try:
            knowledge_store.store_insight(
                ticker=insight.get("ticker", ""),
                agent_name=insight.get("agent_name", ""),
                insight_type=insight.get("insight_type", ""),
                content=insight.get("content", ""),
                confidence=insight.get("confidence", 0.0),
            )
            results["insights_inserted"] += 1
        except Exception as e:
            logger.warning(f"Insight sync failed: {e}")

    return {
        "status": "success",
        "results": results,
        "timestamp": datetime.now().isoformat(),
    }
