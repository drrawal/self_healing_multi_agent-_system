"""
Semantic Memory – stores reusable facts, strategies, and lessons.

Each entry is a text chunk with optional structured metadata.
Retrieval uses TF-IDF-style keyword scoring (no external vector DB).
For production, swap the scorer for a real embedding store (e.g. pgvector).
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
CREATE TABLE IF NOT EXISTS semantic_entries (
    entry_id   TEXT PRIMARY KEY,
    category   TEXT NOT NULL,
    content    TEXT NOT NULL,
    metadata   TEXT NOT NULL,   -- JSON
    score      REAL NOT NULL DEFAULT 1.0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_category ON semantic_entries(category);
"""


@dataclass
class SemanticEntry:
    entry_id  : str
    category  : str          # e.g. "repair_strategy", "tool_tip", "failure_pattern"
    content   : str
    metadata  : dict = field(default_factory=dict)
    score     : float = 1.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_row(self) -> tuple:
        return (
            self.entry_id, self.category, self.content,
            json.dumps(self.metadata), self.score,
            self.created_at, self.updated_at,
        )

    @classmethod
    def from_row(cls, row: tuple) -> "SemanticEntry":
        return cls(
            entry_id  = row[0],
            category  = row[1],
            content   = row[2],
            metadata  = json.loads(row[3]),
            score     = row[4],
            created_at= row[5],
            updated_at= row[6],
        )


class SemanticMemory:
    """
    Key-value + text-search store for persistent facts and strategies.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        settings   = get_settings()
        path       = db_path or settings.memory_db_path
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._k    = settings.semantic_memory_k

    @asynccontextmanager
    async def _connect(self):
        """Async context manager for a fresh DB connection."""
        async with aiosqlite.connect(str(self._path)) as conn:
            await conn.executescript(_CREATE_TABLE)
            await conn.commit()
            yield conn

    async def store(
        self,
        content  : str,
        category : str,
        metadata : Optional[dict] = None,
        entry_id : Optional[str] = None,
    ) -> str:
        import uuid
        eid = entry_id or str(uuid.uuid4())
        entry = SemanticEntry(
            entry_id = eid,
            category = category,
            content  = content,
            metadata = metadata or {},
        )
        async with self._connect() as conn:
            await conn.execute(
                "INSERT OR REPLACE INTO semantic_entries VALUES (?,?,?,?,?,?,?)",
                entry.to_row(),
            )
            await conn.commit()
        return eid

    async def search(
        self,
        query    : str,
        category : Optional[str] = None,
        top_k    : Optional[int] = None,
    ) -> list[SemanticEntry]:
        k = top_k or self._k
        async with self._connect() as conn:
            sql  = "SELECT * FROM semantic_entries"
            args : list = []
            if category:
                sql  += " WHERE category = ?"
                args  = [category]
            sql += " ORDER BY score DESC, updated_at DESC LIMIT 500"
            async with conn.execute(sql, args) as cursor:
                rows = await cursor.fetchall()

        entries = [SemanticEntry.from_row(r) for r in rows]
        return _rank_entries(query, entries)[:k]

    async def reinforce(self, entry_id: str, delta: float = 0.1) -> None:
        """Increase the score of a successful strategy."""
        async with self._connect() as conn:
            await conn.execute(
                "UPDATE semantic_entries SET score = score + ?, updated_at = ? WHERE entry_id = ?",
                (delta, time.time(), entry_id),
            )
            await conn.commit()

    async def decay(self, entry_id: str, delta: float = 0.05) -> None:
        """Decrease the score of a failed strategy."""
        async with self._connect() as conn:
            await conn.execute(
                "UPDATE semantic_entries SET score = MAX(0.0, score - ?), updated_at = ? "
                "WHERE entry_id = ?",
                (delta, time.time(), entry_id),
            )
            await conn.commit()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _rank_entries(query: str, entries: list[SemanticEntry]) -> list[SemanticEntry]:
    query_tokens = set(query.lower().split())
    scored: list[tuple[float, SemanticEntry]] = []
    for e in entries:
        tokens  = set(e.content.lower().split())
        overlap = len(query_tokens & tokens) / max(len(query_tokens), 1)
        total   = e.score * (1.0 + overlap)
        scored.append((total, e))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [e for _, e in scored]
