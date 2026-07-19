"""
Base tool – every callable tool must inherit from this class.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import structlog

log = structlog.get_logger(__name__)


class BaseTool(ABC):
    """
    Contract for all enterprise tools.

    Subclasses must implement:
      - ``name``          – unique identifier
      - ``description``   – human-readable description
      - ``run_async()``   – async execution
    """

    name       : str
    description: str

    @abstractmethod
    async def run_async(self, parameters: dict[str, Any]) -> Any:
        """Execute the tool with the given parameters."""

    def describe(self) -> str:
        """Return a one-line description for the planner prompt."""
        return f"{self.name}: {self.description}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
