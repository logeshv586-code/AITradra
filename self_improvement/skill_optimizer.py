"""
self_improvement/skill_optimizer.py
────────────────────────────────────────────────────────────────────────────────
SkillOptimizer — train agent skills like weights (microsoft/SkillOpt-inspired).

Core idea from SkillOpt: the model stays frozen; the only trainable state is
each agent's SKILL DOCUMENT — a short list of learned trading rules injected
into its system prompt. Training runs as epochs:

  ROLLOUT   — agents trade/predict normally; the SelfImprovementEngine scores
              every prediction and ReflectionMemory logs per-outcome lessons.
  REFLECT   — build a report card per agent (hit rate, recent failures) and
              propose a SMALL number of edits (textual learning rate: max
              MAX_EDITS_PER_EPOCH ops per epoch, MAX_RULES cap on the doc).
  UPDATE    — apply accepted edits as a new skill VERSION; the previous
              version is kept for rollback.
  VALIDATE  — after MIN_VALIDATION_SAMPLES new scored outcomes, compare the
              agent's windowed accuracy since activation against the
              pre-activation baseline. If it degraded beyond TOLERANCE, the
              version is ROLLED BACK and its edits land in the rejected-edit
              buffer so they are never proposed again.

Learned docs live at skills/learned/<AgentName>.md and are injected into
prompts through the existing SkillManager pipeline — zero inference-time
overhead beyond a few hundred prompt tokens, exactly like SkillOpt's
`best_skill.md` artifact.

Works offline: without an LLM, edits are proposed by deterministic
heuristics computed from the report card.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

DB_PATH = settings.KNOWLEDGE_DB_PATH
LEARNED_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills" / "learned"

MAX_EDITS_PER_EPOCH = 3      # textual "learning rate"
MAX_RULES = 12               # cap on doc size (~keeps it under ~2k tokens)
MIN_SAMPLES_FOR_EPOCH = 5    # outcomes needed before we dare edit a skill
MIN_VALIDATION_SAMPLES = 5   # outcomes needed before judging a version
TOLERANCE = 0.03             # accuracy drop tolerated before rollback

REFLECT_SYSTEM = (
    "You are a prompt-engineering coach for trading analysis agents. Given an "
    "agent's track record and current learned rules, propose AT MOST {max_edits} "
    "edits that would improve future accuracy. Rules must be short, actionable, "
    "and derived from the failures shown. Return VALID JSON only:\n"
    '{{"edits": [{{"op": "add", "text": "<new rule>"}}, '
    '{{"op": "replace", "index": <1-based rule number>, "text": "<new text>"}}, '
    '{{"op": "delete", "index": <1-based rule number>}}]}}'
)


class SkillOptimizer:
    """Optimizes per-agent learned skill documents with validation-gated updates."""

    def __init__(self, db_path: str = DB_PATH, skills_dir: Optional[Path] = None):
        self.db_path = db_path
        self.skills_dir = Path(skills_dir) if skills_dir else LEARNED_SKILLS_DIR
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_tables()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _ensure_tables(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS skill_versions (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name        TEXT NOT NULL,
                version           INTEGER NOT NULL,
                content           TEXT NOT NULL,
                edits_json        TEXT,
                baseline_accuracy REAL,
                status            TEXT DEFAULT 'active',  -- active | superseded | rolled_back
                activated_at      TEXT DEFAULT (datetime('now')),
                judged_at         TEXT,
                UNIQUE(agent_name, version)
            );
            CREATE TABLE IF NOT EXISTS skill_rejected_edits (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name  TEXT NOT NULL,
                edit_text   TEXT NOT NULL,
                reason      TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_skillver_agent ON skill_versions(agent_name, version DESC);
        """)
        conn.commit()

    # ── Skill document handling ──────────────────────────────────────────────

    def _skill_path(self, agent_name: str) -> Path:
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", agent_name)
        return self.skills_dir / f"{safe}.md"

    def get_rules(self, agent_name: str) -> list[str]:
        """Parse the learned doc into its numbered rules."""
        path = self._skill_path(agent_name)
        if not path.exists():
            return []
        rules = []
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*\d+\.\s+(.*\S)\s*$", line)
            if m:
                rules.append(m.group(1))
        return rules

    def _write_rules(self, agent_name: str, rules: list[str]) -> str:
        content = (
            f"# Learned Trading Rules — {agent_name}\n"
            f"# Auto-optimized by SkillOptimizer; do not edit by hand.\n\n"
            + "\n".join(f"{i}. {r}" for i, r in enumerate(rules, 1))
            + "\n"
        )
        self._skill_path(agent_name).write_text(content, encoding="utf-8")
        # Invalidate the SkillManager prompt cache so agents see the update
        try:
            from core.skill_manager import skill_manager
            skill_manager.clear_learned_cache(agent_name)
        except Exception:
            pass
        return content

    # ── Accuracy windows (validation signal) ─────────────────────────────────

    def _windowed_accuracy(
        self, agent_name: str, since: Optional[str] = None, until: Optional[str] = None,
    ) -> tuple[Optional[float], int]:
        """Average scored accuracy for an agent from trade_lessons in a window."""
        conn = self._get_conn()
        query = "SELECT AVG(accuracy) AS avg_acc, COUNT(*) AS n FROM trade_lessons WHERE source_agent = ?"
        params: list[Any] = [agent_name]
        if since:
            query += " AND created_at >= ?"
            params.append(since)
        if until:
            query += " AND created_at < ?"
            params.append(until)
        row = conn.execute(query, params).fetchone()
        n = row["n"] or 0
        return (round(row["avg_acc"], 4) if row["avg_acc"] is not None else None), n

    def _trainable_agents(self) -> list[str]:
        """Agents with enough scored outcomes to justify an edit epoch."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT source_agent, COUNT(*) AS n FROM trade_lessons
            WHERE source_agent IS NOT NULL AND source_agent != 'unknown'
            GROUP BY source_agent HAVING n >= ?
        """, (MIN_SAMPLES_FOR_EPOCH,)).fetchall()
        return [r["source_agent"] for r in rows]

    # ── Edit proposal ────────────────────────────────────────────────────────

    def _rejected_edits(self, agent_name: str) -> list[str]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT edit_text FROM skill_rejected_edits WHERE agent_name = ? ORDER BY created_at DESC LIMIT 20",
            (agent_name,),
        ).fetchall()
        return [r["edit_text"] for r in rows]

    async def _propose_edits_llm(self, agent_name: str, report: dict, rules: list[str]) -> Optional[list[dict]]:
        try:
            from llm.client import get_shared_llm
            llm = get_shared_llm()
            rules_block = "\n".join(f"{i}. {r}" for i, r in enumerate(rules, 1)) or "(no rules yet)"
            failures = "\n".join(
                f"- {f['ticker']} {f['direction']}: {f['lesson'][:180]}"
                for f in report.get("recent_failures", [])
            ) or "(none)"
            rejected = "\n".join(f"- {e[:150]}" for e in self._rejected_edits(agent_name)) or "(none)"
            raw = await llm.complete(
                prompt=(
                    f"AGENT: {agent_name}\n"
                    f"HIT RATE: {report.get('hit_rate')} over {report.get('total_lessons')} outcomes "
                    f"(avg accuracy {report.get('avg_accuracy')})\n\n"
                    f"CURRENT LEARNED RULES:\n{rules_block}\n\n"
                    f"RECENT FAILURES:\n{failures}\n\n"
                    f"PREVIOUSLY REJECTED EDITS (do NOT re-propose):\n{rejected}\n\n"
                    "Propose your edits now."
                ),
                system=REFLECT_SYSTEM.format(max_edits=MAX_EDITS_PER_EPOCH),
                expect_json=True,
                temperature=0.2,
                max_tokens=500,
                role="analysis",
            )
            data = json.loads(raw) if isinstance(raw, str) else raw
            edits = data.get("edits", [])
            return edits[:MAX_EDITS_PER_EPOCH] if edits else None
        except Exception as e:
            logger.debug(f"[SkillOptimizer] LLM edit proposal skipped for {agent_name}: {e}")
            return None

    @staticmethod
    def _propose_edits_heuristic(report: dict, rules: list[str]) -> list[dict]:
        """Deterministic fallback: derive rules directly from the report card."""
        edits: list[dict] = []
        hit_rate = report.get("hit_rate")
        failures = report.get("recent_failures", [])

        if hit_rate is not None and hit_rate < 0.45 and failures:
            # Find the dominant failing direction
            directions = [f.get("direction", "") for f in failures]
            worst = max(set(directions), key=directions.count) if directions else ""
            tickers = ", ".join(sorted({f.get("ticker", "") for f in failures})[:4])
            rule = (
                f"Recent {worst} calls underperformed (hit rate {hit_rate:.0%}, e.g. on {tickers}). "
                f"Require at least two independent confirming signals before issuing {worst} again."
            )
            if rule not in rules:
                edits.append({"op": "add", "text": rule})
        elif hit_rate is not None and hit_rate > 0.65:
            rule = (
                f"Track record is strong (hit rate {hit_rate:.0%} over "
                f"{report.get('total_lessons')} outcomes) — maintain current methodology "
                "and prefer decisive signals over hedged NEUTRAL output."
            )
            if rule not in rules:
                edits.append({"op": "add", "text": rule})
        return edits[:MAX_EDITS_PER_EPOCH]

    @staticmethod
    def apply_edits(rules: list[str], edits: list[dict]) -> list[str]:
        """Apply add/replace/delete ops to the rule list (SkillOpt edit ops)."""
        new_rules = list(rules)
        # Deletes/replaces first (index-based), then adds
        for edit in sorted(
            [e for e in edits if e.get("op") in ("replace", "delete")],
            key=lambda e: -int(e.get("index", 0)),
        ):
            idx = int(edit.get("index", 0)) - 1
            if 0 <= idx < len(new_rules):
                if edit["op"] == "delete":
                    new_rules.pop(idx)
                else:
                    text = str(edit.get("text", "")).strip()
                    if text:
                        new_rules[idx] = text
        for edit in edits:
            if edit.get("op") == "add":
                text = str(edit.get("text", "")).strip()
                if text and text not in new_rules:
                    new_rules.append(text)
        return new_rules[:MAX_RULES]

    # ── Epoch: reflect → update ──────────────────────────────────────────────

    async def run_epoch(self, use_llm: bool = True) -> dict:
        """One optimization epoch across all trainable agents."""
        from memory.reflection_memory import get_memory

        results = {"updated": [], "skipped": [], "validated": []}

        # 1. Validation gate first: judge (and maybe roll back) earlier versions
        results["validated"] = self.validate_active_versions()

        # 2. Propose + apply edits per agent
        for agent_name in self._trainable_agents():
            report = get_memory().get_agent_report_card(agent_name)
            rules = self.get_rules(agent_name)

            edits = None
            if use_llm:
                edits = await self._propose_edits_llm(agent_name, report, rules)
            if not edits:
                edits = self._propose_edits_heuristic(report, rules)
            if not edits:
                results["skipped"].append({"agent": agent_name, "reason": "no useful edits proposed"})
                continue

            new_rules = self.apply_edits(rules, edits)
            if new_rules == rules:
                results["skipped"].append({"agent": agent_name, "reason": "edits were no-ops"})
                continue

            content = self._write_rules(agent_name, new_rules)
            baseline, _ = self._windowed_accuracy(agent_name)
            version = self._next_version(agent_name)
            conn = self._get_conn()
            conn.execute(
                "UPDATE skill_versions SET status = 'superseded' WHERE agent_name = ? AND status = 'active'",
                (agent_name,),
            )
            conn.execute("""
                INSERT INTO skill_versions (agent_name, version, content, edits_json, baseline_accuracy)
                VALUES (?, ?, ?, ?, ?)
            """, (agent_name, version, content, json.dumps(edits, ensure_ascii=False), baseline))
            conn.commit()
            results["updated"].append({
                "agent": agent_name, "version": version,
                "edits": edits, "baseline_accuracy": baseline,
            })
            logger.info(f"[SkillOptimizer] {agent_name} → skill v{version} ({len(edits)} edits)")

        return results

    def _next_version(self, agent_name: str) -> int:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT MAX(version) AS v FROM skill_versions WHERE agent_name = ?", (agent_name,)
        ).fetchone()
        return (row["v"] or 0) + 1

    # ── Validation gate + rollback ───────────────────────────────────────────

    def validate_active_versions(self) -> list[dict]:
        """
        Judge each active version once enough post-activation outcomes exist.
        Roll back versions whose windowed accuracy dropped beyond TOLERANCE.
        """
        conn = self._get_conn()
        judged: list[dict] = []
        actives = conn.execute("""
            SELECT id, agent_name, version, content, edits_json, baseline_accuracy, activated_at
            FROM skill_versions WHERE status = 'active' AND judged_at IS NULL
        """).fetchall()

        for ver in actives:
            post_acc, n = self._windowed_accuracy(ver["agent_name"], since=ver["activated_at"])
            if n < MIN_VALIDATION_SAMPLES or post_acc is None:
                continue  # not enough evidence yet — keep collecting

            baseline = ver["baseline_accuracy"]
            now = datetime.now(timezone.utc).isoformat()
            if baseline is not None and post_acc < baseline - TOLERANCE:
                # Degradation → roll back to the previous version's content
                prev = conn.execute("""
                    SELECT content FROM skill_versions
                    WHERE agent_name = ? AND version < ? ORDER BY version DESC LIMIT 1
                """, (ver["agent_name"], ver["version"])).fetchone()
                if prev:
                    self._skill_path(ver["agent_name"]).write_text(prev["content"], encoding="utf-8")
                else:
                    self._skill_path(ver["agent_name"]).unlink(missing_ok=True)
                try:
                    from core.skill_manager import skill_manager
                    skill_manager.clear_learned_cache(ver["agent_name"])
                except Exception:
                    pass

                # Buffer the rejected edits so they are never re-proposed
                for edit in json.loads(ver["edits_json"] or "[]"):
                    conn.execute("""
                        INSERT INTO skill_rejected_edits (agent_name, edit_text, reason)
                        VALUES (?, ?, ?)
                    """, (
                        ver["agent_name"],
                        edit.get("text", json.dumps(edit)),
                        f"v{ver['version']} accuracy {post_acc} < baseline {baseline} - {TOLERANCE}",
                    ))
                conn.execute(
                    "UPDATE skill_versions SET status = 'rolled_back', judged_at = ? WHERE id = ?",
                    (now, ver["id"]),
                )
                judged.append({
                    "agent": ver["agent_name"], "version": ver["version"],
                    "outcome": "rolled_back", "baseline": baseline, "post": post_acc, "samples": n,
                })
                logger.warning(
                    f"[SkillOptimizer] Rolled back {ver['agent_name']} v{ver['version']} "
                    f"(accuracy {baseline} → {post_acc})"
                )
            else:
                conn.execute(
                    "UPDATE skill_versions SET judged_at = ? WHERE id = ?", (now, ver["id"])
                )
                judged.append({
                    "agent": ver["agent_name"], "version": ver["version"],
                    "outcome": "kept", "baseline": baseline, "post": post_acc, "samples": n,
                })
        conn.commit()
        return judged

    # ── Status ───────────────────────────────────────────────────────────────

    def status(self) -> dict:
        conn = self._get_conn()
        versions = conn.execute("""
            SELECT agent_name, version, status, baseline_accuracy, activated_at, judged_at
            FROM skill_versions ORDER BY agent_name, version DESC
        """).fetchall()
        rejected = conn.execute(
            "SELECT COUNT(*) AS n FROM skill_rejected_edits"
        ).fetchone()["n"]
        return {
            "trainable_agents": self._trainable_agents(),
            "versions": [dict(v) for v in versions],
            "rejected_edits_buffered": rejected,
            "learned_skills_dir": str(self.skills_dir),
            "config": {
                "max_edits_per_epoch": MAX_EDITS_PER_EPOCH,
                "max_rules": MAX_RULES,
                "min_samples_for_epoch": MIN_SAMPLES_FOR_EPOCH,
                "min_validation_samples": MIN_VALIDATION_SAMPLES,
                "rollback_tolerance": TOLERANCE,
            },
        }


# ── Module-level singleton ────────────────────────────────────────────────────

_optimizer_instance: Optional[SkillOptimizer] = None


def get_optimizer() -> SkillOptimizer:
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = SkillOptimizer()
    return _optimizer_instance
