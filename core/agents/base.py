"""
Abstract base for all agents.
Provides identity, lifecycle hooks, and structured logging.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any

import structlog

from config.settings import get_settings


class BaseAgent(ABC):
    """
    Contract every agent must fulfil:
      - ``name``   – human-readable agent identifier
      - ``run()``  – main async entry point
    """

    def __init__(self, name: str) -> None:
        self.agent_id = str(uuid.uuid4())
        self.name     = name
        self._log     = structlog.get_logger(self.__class__.__name__).bind(
            agent_id=self.agent_id, agent_name=name
        )
        self._settings = get_settings()

    @abstractmethod
    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute agent logic. Returns updated context fragment."""

    async def on_start(self, context: dict) -> None:
        """Hook called before ``run``. Override for setup logic."""
        self._log.debug("agent.start")

    async def on_complete(self, context: dict, result: dict) -> None:
        """Hook called after successful ``run``."""
        self._log.debug("agent.complete")

    async def on_error(self, context: dict, exc: Exception) -> None:
        """Hook called when ``run`` raises."""
        self._log.error("agent.error", error=str(exc))

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Lifecycle wrapper:
            on_start → run → on_complete (or on_error)
        """
        await self.on_start(context)
        try:
            result = await self.run(context)
            await self.on_complete(context, result)
            return result
        except Exception as exc:
            await self.on_error(context, exc)
            raise

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, id={self.agent_id[:8]})"
