"""
Tool Registry – global catalogue of available tools.

Usage
-----
registry = ToolRegistry.instance()
tool     = registry.get("web_search")
result   = await tool.run_async({"query": "..."})
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

import structlog

from tools.base import BaseTool

log = structlog.get_logger(__name__)


class ToolRegistry:
    """Singleton registry; tools are registered at import time."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._bootstrap()

    @classmethod
    @lru_cache(maxsize=1)
    def instance(cls) -> "ToolRegistry":
        return cls()

    def register(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            log.warning("registry.overwrite", tool=tool.name)
        self._tools[tool.name] = tool
        log.debug("registry.registered", tool=tool.name)

    def get(self, name: str) -> BaseTool:
        tool = self._tools.get(name)
        if tool is None:
            # Graceful fallback: return a no-op tool instead of raising
            log.warning("registry.not_found", tool=name)
            return self._tools.get("noop")   # type: ignore[return-value]
        return tool

    def describe_all(self) -> str:
        return "\n".join(t.describe() for t in self._tools.values())

    def list_names(self) -> list[str]:
        return list(self._tools.keys())

    # ── Bootstrap ──────────────────────────────────────────────────

    def _bootstrap(self) -> None:
        """Import and register all built-in enterprise tools."""
        from tools.enterprise.web_search   import WebSearchTool
        from tools.enterprise.database     import DatabaseQueryTool
        from tools.enterprise.api_client   import APIClientTool
        from tools.enterprise.file_proc    import FileProcessorTool
        from tools.enterprise.notifier     import NotifierTool
        from tools.enterprise.noop         import NoOpTool

        for tool_cls in [
            NoOpTool,
            WebSearchTool,
            DatabaseQueryTool,
            APIClientTool,
            FileProcessorTool,
            NotifierTool,
        ]:
            self.register(tool_cls())

        log.info("registry.bootstrapped", count=len(self._tools))
