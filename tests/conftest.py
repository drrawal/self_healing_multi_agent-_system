"""
Shared pytest fixtures.
"""
from __future__ import annotations

import asyncio
import pytest

from config.logging_config import configure_logging


@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    configure_logging()


@pytest.fixture
def sample_state():
    """Minimal valid AgentState dict for unit tests."""
    import time, uuid
    return {
        "task_id"          : str(uuid.uuid4()),
        "objective"        : "Test objective for unit testing",
        "plan"             : [],
        "current_step_index": 0,
        "step_results"     : [],
        "failures"         : [],
        "repair_count"     : 0,
        "max_repairs"      : 3,
        "status"           : "executing",
        "learned_context"  : {},
        "knowledge_snapshot": {},
        "start_time"       : time.time(),
        "metrics"          : {},
        "messages"         : [],
    }


@pytest.fixture
def sample_failure():
    return {
        "failure_id"  : "test-fail-01",
        "step_id"     : "step-01",
        "failure_type": "network",
        "severity"    : "high",
        "description" : "Connection timed out",
        "raw_error"   : "connection timed out after 30s",
        "resolved"    : False,
    }


@pytest.fixture
def sample_step():
    return {
        "step_id"     : "step-01",
        "description" : "Search for relevant documents",
        "tool"        : "web_search",
        "parameters"  : {"query": "AI research 2024"},
        "dependencies": [],
        "retry_count" : 0,
        "max_retries" : 2,
        "is_optional" : False,
        "fallback_tool": "database_query",
        "timeout_seconds": 60,
    }
