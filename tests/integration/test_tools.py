"""
Integration tests for the enterprise tools.
These run against the real tool implementations (no mocks).
"""
from __future__ import annotations

import pytest

from tools.enterprise import (
    APIClientTool, DatabaseQueryTool,
    FileProcessorTool, NoOpTool,
    NotifierTool, WebSearchTool,
)


@pytest.mark.asyncio
async def test_noop_tool():
    tool = NoOpTool()
    result = await tool.run_async({"key": "value"})
    assert result["status"] == "noop"


@pytest.mark.asyncio
async def test_web_search_returns_results():
    tool = WebSearchTool()
    result = await tool.run_async({"query": "self-healing agents", "max_results": 3})
    assert "results" in result
    assert len(result["results"]) == 3


@pytest.mark.asyncio
async def test_database_query_select():
    tool = DatabaseQueryTool()
    result = await tool.run_async({"sql": "SELECT * FROM users LIMIT 10"})
    assert "rows" in result


@pytest.mark.asyncio
async def test_database_query_rejects_write():
    tool = DatabaseQueryTool()
    with pytest.raises(ValueError, match="Only SELECT"):
        await tool.run_async({"sql": "DROP TABLE users"})


@pytest.mark.asyncio
async def test_api_call_tool():
    tool = APIClientTool()
    result = await tool.run_async({"url": "https://api.example.com/data", "method": "GET"})
    assert result["status_code"] == 200


@pytest.mark.asyncio
async def test_notifier_sends():
    tool = NotifierTool()
    result = await tool.run_async({"channel": "slack", "message": "Test notification"})
    assert result["delivered"] is True


@pytest.mark.asyncio
async def test_tool_synthetic_failure():
    """Verify that failure_rate injection works for experiments."""
    tool = WebSearchTool()
    tool.failure_rate = 1.0   # 100% failure
    with pytest.raises(ConnectionError):
        await tool.run_async({"query": "test"})
    tool.failure_rate = 0.0   # restore
