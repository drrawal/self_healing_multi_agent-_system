"""
Episodic Memory – records every task execution as a retrievable episode.

An episode contains:
  - The original objective
  - The full execution plan
  - Step results (success/failure)
  - Failures with root-cause analyses
  - Repair attempts and outcomes
  - Final status and metrics

Storage: SQLite via aiosqlite (no heavy ORM dependency here).
Retrieval: keyword + recency scoring (no vector DB required for research baseline).
"""
from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import aiosqlite
import structlog

from config.settings import get_settings

log = structlog.get_logger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS episodes (
    episode_id   TEXT PRIMARY KEY,
    task_id      TEXT NOT NULL,
    objective    TEXT NOT NULL,
    status       TEXT NOT NULL,
    plan         TEXT NOT NULL,   -- JSON
    step_results TEXT NOT NULL,   -- JSON
    failures     TEXT NOT NULL,   -- JSON
    metrics      TEXT NOT NULL,   -- JSON
    created_at   REAL NOT NULL,
    duration_ms  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_objective ON episodes(objective);
CREATE INDEX IF NOT EXISTS idx_status    ON episodes(status);
CREATE INDEX IF NOT EXISTS idx_created   ON episodes(created_at);
"""


@dataclass
class Episode:
    episode_id : str
    task_id    : str
    objective  : str
    status     : str
    plan       : list[dict]
    step_results: list[dict]
    failures   : list[dict]
    metrics    : dict
    created_at : float = field(default_factory=time.time)
    duration_ms: float = 0.0

    def to_row(self) -> tuple:
        return (
            self.episode_id,
            self.task_id,
            self.objective,
            self.status,
            json.dumps(self.plan),
            json.dumps(self.step_results),
            json.dumps(self.failures),
            json.dumps(self.metrics),
            self.created_at,
            self.duration_ms,
        )

    @classmethod
    def from_row(cls, row: tuple) -> "Episode":
        return cls(
            episode_id  = row[0],
            task_id     = row[1],
            objective   = row[2],
            status      = row[3],
            plan        = json.loads(row[4]),
            step_results= json.loads(row[5]),
            failures    = json.loads(row[6]),
            metrics     = json.loads(row[7]),
            created_at  = row[8],
            duration_ms = row[9],
        )


class EpisodicMemory:
    """
    Append-only log of task executions.
    Provides similarity-based retrieval using keyword overlap.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        settings   = get_settings()
        path       = db_path or settings.memory_db_path
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._limit= settings.episodic_memory_limit

    @asynccontextmanager
    async def _connect(self):
        """Async context manager for a fresh DB connection."""
        async with aiosqlite.connect(str(self._path)) as conn:
            await conn.executescript(_CREATE_TABLE)
            await conn.commit()
            yield conn

    async def store(self, state: dict) -> str:
        """Persist a completed execution as an episode. Returns episode_id."""
        import uuid
        episode = Episode(
            episode_id  = str(uuid.uuid4()),
            task_id     = state["task_id"],
            objective   = state["objective"],
            status      = state.get("status", "unknown"),
            plan        = state.get("plan", []),
            step_results= state.get("step_results", []),
            failures    = state.get("failures", []),
            metrics     = state.get("metrics", {}),
            duration_ms = (time.time() - state.get("start_time", time.time())) * 1000,
        )

        async with self._connect() as conn:
            await conn.execute(
                """INSERT INTO episodes VALUES (?,?,?,?,?,?,?,?,?,?)""",
                episode.to_row(),
            )
            await conn.commit()
            await self._enforce_limit(conn)

        log.debug("episodic.stored", episode_id=episode.episode_id)
        return episode.episode_id

    async def recall(
        self,
        query: str,
        top_k: int = 5,
        status_filter: Optional[str] = None,
    ) -> list[Episode]:
        """
        Retrieve the top-k most relevant episodes for ``query``.
        Scoring = keyword overlap × recency decay.
        """
        async with self._connect() as conn:
            sql  = "SELECT * FROM episodes"
            args: list = []
            if status_filter:
                sql  += " WHERE status = ?"
                args  = [status_filter]
            sql += " ORDER BY created_at DESC LIMIT 200"

            async with conn.execute(sql, args) as cursor:
                rows = await cursor.fetchall()

        episodes = [Episode.from_row(r) for r in rows]
        scored   = _score_episodes(query, episodes)
        return scored[:top_k]

    async def recall_strategies(self, query: str, top_k: int = 5) -> str:
        """
        High-level helper used by the planner node.
        Returns a formatted string of repair strategies from past episodes.
        """
        episodes = await self.recall(query, top_k=top_k, status_filter="completed")
        if not episodes:
            return ""

        lines = ["Relevant past executions:"]
        for ep in episodes:
            healed = [f for f in ep.failures if f.get("resolved")]
            if healed:
                for f in healed:
                    lines.append(
                        f"  - Failure type {f.get('failure_type')} resolved with "
                        f"{f.get('repair_strategy')} – {f.get('root_cause', '')[:80]}"
                    )
        return "\n".join(lines) if len(lines) > 1 else ""

    async def _enforce_limit(self, conn: aiosqlite.Connection) -> None:
        """Remove oldest episodes when over the limit."""
        async with conn.execute("SELECT COUNT(*) FROM episodes") as cur:
            count = (await cur.fetchone())[0]

        if count > self._limit:
            excess = count - self._limit
            await conn.execute(
                "DELETE FROM episodes WHERE episode_id IN "
                "(SELECT episode_id FROM episodes ORDER BY created_at ASC LIMIT ?)",
                (excess,),
            )
            await conn.commit()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _score_episodes(query: str, episodes: list[Episode]) -> list[Episode]:
    """Score episodes by keyword overlap + recency."""
    if not episodes:
        return []

    query_tokens = set(query.lower().split())
    now          = time.time()
    scored: list[tuple[float, Episode]] = []

    for ep in episodes:
        obj_tokens = set(ep.objective.lower().split())
        overlap    = len(query_tokens & obj_tokens) / max(len(query_tokens), 1)
        age_days   = (now - ep.created_at) / 86_400
        recency    = 1.0 / (1.0 + age_days * 0.1)   # gentle decay
        score      = 0.7 * overlap + 0.3 * recency
        scored.append((score, ep))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [ep for _, ep in scored]
