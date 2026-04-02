"""Local plugin registry for optional market-intelligence signal sources."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

MANIFEST_PATH = (Path(settings.DATA_DIR) / "local_intel_plugins.json").resolve()

DEFAULT_PLUGINS = [
    {
        "id": "knowledge-store",
        "name": "Knowledge Store Cache",
        "type": "database",
        "enabled": True,
        "mode": "local",
        "cadence": "continuous",
        "description": "Primary local SQLite warehouse for OHLCV, news, and intelligence snapshots.",
    },
    {
        "id": "rss-news",
        "name": "RSS News Collector",
        "type": "scraper",
        "enabled": True,
        "mode": "local",
        "cadence": "10m",
        "description": "Deduplicated market news ingestion from RSS feeds.",
    },
    {
        "id": "social-sentiment",
        "name": "Social Sentiment Feed",
        "type": "sentiment",
        "enabled": True,
        "mode": "local",
        "cadence": "15m",
        "description": "Local social sentiment scoring used by the intelligence layer.",
    },
    {
        "id": "web-catalyst",
        "name": "Web Catalyst Scraper",
        "type": "scraper",
        "enabled": True,
        "mode": "on_demand",
        "cadence": "manual",
        "description": "On-demand catalyst scraping for ticker-specific deep research.",
    },
    {
        "id": "mirofish-local-mirror",
        "name": "MiroFish Local Mirror",
        "type": "github_mirror",
        "enabled": False,
        "mode": "local_plugin",
        "cadence": "daily",
        "path": "data/plugins/mirofish",
        "description": "Reserved local plugin slot for exported open-source GitHub agent data such as MiroFish or similar community signal bundles.",
    },
]


def _safe_json_load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning(f"Failed to parse plugin file {path}: {exc}")
        return None


def _minutes_since(ts: datetime | None) -> int | None:
    if ts is None:
        return None
    return max(int((datetime.now() - ts).total_seconds() // 60), 0)


class LocalPluginRegistry:
    def __init__(self, manifest_path: Path = MANIFEST_PATH):
        self.manifest_path = manifest_path

    def _load_manifest(self) -> list[dict]:
        if not self.manifest_path.exists():
            return list(DEFAULT_PLUGINS)
        try:
            raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                return raw
        except Exception as exc:
            logger.warning(f"Failed to read plugin manifest {self.manifest_path}: {exc}")
        return list(DEFAULT_PLUGINS)

    def _resolve_path(self, value: str | None) -> Path | None:
        if not value:
            return None
        path = Path(value)
        if not path.is_absolute():
            path = Path.cwd() / path
        return path.resolve()

    def _plugin_status(self, plugin: dict) -> tuple[str, int | None]:
        plugin_path = self._resolve_path(plugin.get("path"))
        enabled = bool(plugin.get("enabled", False))
        if plugin_path:
            if plugin_path.exists():
                modified = datetime.fromtimestamp(plugin_path.stat().st_mtime)
                if enabled:
                    return "active", _minutes_since(modified)
                return "ready", _minutes_since(modified)
            return ("awaiting_local_data" if not enabled else "degraded"), None
        return ("active" if enabled else "disabled"), None

    def get_plugins(self) -> list[dict]:
        plugins: list[dict] = []
        for raw in self._load_manifest():
            plugin = dict(raw)
            plugin_path = self._resolve_path(plugin.get("path"))
            status, freshness_minutes = self._plugin_status(plugin)
            plugins.append(
                {
                    **plugin,
                    "status": status,
                    "path": str(plugin_path) if plugin_path else None,
                    "freshness_minutes": freshness_minutes,
                }
            )
        return plugins

    def get_summary(self) -> dict:
        plugins = self.get_plugins()
        active = sum(1 for plugin in plugins if plugin["status"] == "active")
        ready = sum(1 for plugin in plugins if plugin["status"] == "ready")
        waiting = sum(1 for plugin in plugins if plugin["status"] == "awaiting_local_data")
        return {
            "total": len(plugins),
            "active": active,
            "ready": ready,
            "awaiting_local_data": waiting,
        }

    def load_signals(self, limit: int = 1000) -> list[dict]:
        """Load plugin signals from local JSON mirrors.

        Supported file shapes:
        - [{"ticker": "AAPL", "signal": "BUY", ...}]
        - {"signals": [{...}, ...]}
        """
        signals: list[dict] = []
        for plugin in self.get_plugins():
            plugin_path_str = plugin.get("path")
            if not plugin_path_str or plugin.get("status") not in {"active", "ready"}:
                continue

            plugin_path = Path(plugin_path_str)
            json_files: list[Path] = []
            if plugin_path.is_file() and plugin_path.suffix.lower() == ".json":
                json_files = [plugin_path]
            elif plugin_path.is_dir():
                json_files = sorted(plugin_path.rglob("*.json"))

            for json_file in json_files:
                payload = _safe_json_load(json_file)
                if payload is None:
                    continue
                if isinstance(payload, dict):
                    items = payload.get("signals", [])
                elif isinstance(payload, list):
                    items = payload
                else:
                    items = []

                for item in items:
                    if not isinstance(item, dict):
                        continue
                    ticker = str(item.get("ticker", "")).upper().strip()
                    if not ticker:
                        continue
                    signals.append(
                        {
                            "plugin_id": plugin.get("id"),
                            "plugin_name": plugin.get("name"),
                            "ticker": ticker,
                            "signal": str(item.get("signal", item.get("recommendation", "HOLD"))).upper(),
                            "confidence": float(item.get("confidence", 0) or 0),
                            "horizon": item.get("horizon", item.get("time_horizon", "")),
                            "reason": item.get("reason", item.get("summary", "")),
                            "as_of": item.get("as_of", item.get("updated_at")),
                            "source_file": str(json_file),
                        }
                    )
                    if len(signals) >= limit:
                        return signals
        return signals


local_plugin_registry = LocalPluginRegistry()
