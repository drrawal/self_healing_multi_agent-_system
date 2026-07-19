"""
Enterprise tools – each with a configurable synthetic failure rate
for controlled experiments.
"""
from __future__ import annotations

import asyncio
import random
from typing import Any

import structlog

from tools.base import BaseTool

log = structlog.get_logger(__name__)


class _SyntheticFailureMixin:
    """Inject random failures for experiment reproducibility."""

    failure_rate: float = 0.0   # override in subclass or test

    def _maybe_fail(self, label: str) -> None:
        if self.failure_rate > 0 and random.random() < self.failure_rate:
            raise ConnectionError(f"Synthetic {label} failure (rate={self.failure_rate})")


# ── No-Op tool (safe fallback) ─────────────────────────────────────────────────

class NoOpTool(_SyntheticFailureMixin, BaseTool):
    name        = "noop"
    description = "No-operation placeholder; always succeeds."

    async def run_async(self, parameters: dict[str, Any]) -> Any:
        return {"status": "noop", "parameters": parameters}


# ── Web Search ─────────────────────────────────────────────────────────────────

class WebSearchTool(_SyntheticFailureMixin, BaseTool):
    name        = "web_search"
    description = "Search the web for information. Parameters: query (str), max_results (int=5)"
    failure_rate: float = 0.0

    async def run_async(self, parameters: dict[str, Any]) -> Any:
        self._maybe_fail("network")
        query       = parameters.get("query", "")
        max_results = int(parameters.get("max_results", 5))
        await asyncio.sleep(0.05)   # simulate I/O

        # Deterministic mock results
        return {
            "query"  : query,
            "results": [
                {"title": f"Result {i} for '{query}'", "url": f"https://example.com/{i}"}
                for i in range(1, max_results + 1)
            ],
        }


# ── Database Query ─────────────────────────────────────────────────────────────

class DatabaseQueryTool(_SyntheticFailureMixin, BaseTool):
    name        = "database_query"
    description = "Execute a read-only SQL query. Parameters: sql (str), db (str='default')"
    failure_rate: float = 0.0

    async def run_async(self, parameters: dict[str, Any]) -> Any:
        self._maybe_fail("database connection")
        sql = parameters.get("sql", "SELECT 1")
        if not sql.strip().upper().startswith("SELECT"):
            raise ValueError("Only SELECT statements are allowed.")
        await asyncio.sleep(0.03)
        return {"rows": [{"id": 1, "value": "mock_row"}], "sql": sql}


# ── REST API Client ────────────────────────────────────────────────────────────

class APIClientTool(_SyntheticFailureMixin, BaseTool):
    name        = "api_call"
    description = "Make an HTTP GET/POST to an external API. Parameters: url (str), method (str='GET'), payload (dict={})"
    failure_rate: float = 0.0

    async def run_async(self, parameters: dict[str, Any]) -> Any:
        self._maybe_fail("network timeout")
        url     = parameters.get("url", "https://api.example.com")
        method  = parameters.get("method", "GET").upper()
        payload = parameters.get("payload", {})
        await asyncio.sleep(0.08)
        return {"status_code": 200, "url": url, "method": method, "body": {"success": True}}


# ── File Processor ─────────────────────────────────────────────────────────────

class FileProcessorTool(_SyntheticFailureMixin, BaseTool):
    name        = "file_processor"
    description = "Read, parse, or transform a file. Parameters: path (str), operation (str='read')"
    failure_rate: float = 0.0

    async def run_async(self, parameters: dict[str, Any]) -> Any:
        self._maybe_fail("file I/O")
        path      = parameters.get("path", "data/sample.txt")
        operation = parameters.get("operation", "read")
        await asyncio.sleep(0.02)
        return {"path": path, "operation": operation, "lines": 42, "size_kb": 12.5}


# ── Notifier ───────────────────────────────────────────────────────────────────

class NotifierTool(_SyntheticFailureMixin, BaseTool):
    name        = "notifier"
    description = "Send a notification (email/Slack/webhook). Parameters: channel (str), message (str)"
    failure_rate: float = 0.0

    async def run_async(self, parameters: dict[str, Any]) -> Any:
        self._maybe_fail("notification delivery")
        channel = parameters.get("channel", "email")
        message = parameters.get("message", "")
        await asyncio.sleep(0.02)
        log.info("notifier.sent", channel=channel, message=message[:60])
        return {"delivered": True, "channel": channel}
