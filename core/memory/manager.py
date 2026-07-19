"""
MemoryManager – unified facade over episodic and semantic memory.
Both memory stores share the same SQLite file (different tables).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

import structlog

from core.memory.episodic import EpisodicMemory
from core.memory.semantic import SemanticMemory

log = structlog.get_logger(__name__)


class MemoryManager:
    """
    Public interface used by graph nodes and healing components.
    Singleton: call ``MemoryManager.instance()`` rather than ``__init__``.
    """

    def __init__(self) -> None:
        self._episodic = EpisodicMemory()
        self._semantic = SemanticMemory()

    @classmethod
    @lru_cache(maxsize=1)
    def instance(cls) -> "MemoryManager":
        return cls()

    # ── Write ──────────────────────────────────────────────────────

    async def record_execution(self, state: dict) -> str:
        """Store a completed task execution. Returns episode_id."""
        return await self._episodic.store(state)

    async def store_strategy(
        self,
        content  : str,
        failure_type: str,
        tool    : str,
        success : bool,
    ) -> str:
        """Persist a repair strategy with outcome metadata."""
        return await self._semantic.store(
            content  = content,
            category = "repair_strategy",
            metadata = {
                "failure_type": failure_type,
                "tool"        : tool,
                "success"     : success,
            },
        )

    async def store_tool_tip(self, tool: str, tip: str) -> str:
        return await self._semantic.store(
            content  = tip,
            category = "tool_tip",
            metadata = {"tool": tool},
        )

    # ── Read ───────────────────────────────────────────────────────

    async def recall_strategies(self, query: str, top_k: int = 5) -> str:
        """Return formatted repair strategies relevant to ``query``."""
        semantic_hits = await self._semantic.search(
            query    = query,
            category = "repair_strategy",
            top_k    = top_k,
        )
        episodic_text = await self._episodic.recall_strategies(query, top_k=top_k)

        lines = []
        for entry in semantic_hits:
            lines.append(
                f"  [{entry.metadata.get('failure_type', '?')}] "
                f"{entry.content[:120]} "
                f"(score={entry.score:.2f}, "
                f"success={entry.metadata.get('success')})"
            )
        if episodic_text:
            lines.append(episodic_text)
        return "\n".join(lines)

    async def recall_episodes(self, query: str, top_k: int = 5) -> str:
        """Return a prose summary of the most relevant past episodes."""
        episodes = await self._episodic.recall(query, top_k=top_k)
        if not episodes:
            return ""
        lines = [f"Similar past task: '{ep.objective[:60]}' → {ep.status}" for ep in episodes]
        return "\n".join(lines)

    async def reinforce_strategy(self, entry_id: str) -> None:
        await self._semantic.reinforce(entry_id)

    async def decay_strategy(self, entry_id: str) -> None:
        await self._semantic.decay(entry_id)
