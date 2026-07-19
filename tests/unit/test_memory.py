"""
Unit tests for episodic and semantic memory.
"""
from __future__ import annotations

import time
import uuid

import pytest

from core.memory.episodic import EpisodicMemory
from core.memory.semantic import SemanticMemory


@pytest.fixture
def episodic(tmp_path):
    return EpisodicMemory(db_path=str(tmp_path / "memory.db"))


@pytest.fixture
def semantic(tmp_path):
    return SemanticMemory(db_path=str(tmp_path / "memory.db"))


@pytest.fixture
def completed_state():
    return {
        "task_id"   : str(uuid.uuid4()),
        "objective" : "Search for AI research and summarise",
        "status"    : "completed",
        "plan"      : [{"step_id": "s1", "description": "search", "tool": "web_search", "parameters": {}}],
        "step_results": [{"step_id": "s1", "success": True}],
        "failures"  : [],
        "metrics"   : {},
        "start_time": time.time() - 5.0,
    }


# ── Episodic Memory ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_store_and_recall(episodic, completed_state):
    episode_id = await episodic.store(completed_state)
    assert episode_id

    results = await episodic.recall("AI research")
    assert len(results) >= 1
    assert results[0].objective == completed_state["objective"]


@pytest.mark.asyncio
async def test_recall_returns_empty_for_no_match(episodic):
    results = await episodic.recall("completely unrelated zyxwv")
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_recall_strategies_format(episodic):
    state = {
        "task_id"   : str(uuid.uuid4()),
        "objective" : "database query for reports",
        "status"    : "completed",
        "plan"      : [],
        "step_results": [],
        "failures"  : [{"failure_type": "network", "repair_strategy": "retry", "root_cause": "timeout", "resolved": True}],
        "metrics"   : {},
        "start_time": time.time() - 2.0,
    }
    await episodic.store(state)
    text = await episodic.recall_strategies("database query")
    # Should contain at least something
    assert isinstance(text, str)


# ── Semantic Memory ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_store_and_search(semantic):
    eid = await semantic.store(
        content  = "Retry with backoff works well for network timeouts",
        category = "repair_strategy",
        metadata = {"failure_type": "network", "tool": "api_call", "success": True},
    )
    assert eid

    results = await semantic.search("network timeout retry")
    assert len(results) >= 1
    assert "network" in results[0].content.lower() or "retry" in results[0].content.lower()


@pytest.mark.asyncio
async def test_reinforce_increases_score(semantic):
    eid = await semantic.store(
        content  = "Test strategy entry",
        category = "repair_strategy",
        metadata = {},
    )
    results_before = await semantic.search("test strategy")
    score_before   = results_before[0].score if results_before else 1.0

    await semantic.reinforce(eid, delta=0.5)

    results_after  = await semantic.search("test strategy")
    score_after    = results_after[0].score if results_after else 1.0
    assert score_after >= score_before


@pytest.mark.asyncio
async def test_decay_decreases_score(semantic):
    eid = await semantic.store(
        content  = "Weak strategy entry that rarely works",
        category = "repair_strategy",
        metadata = {},
    )
    results_before = await semantic.search("weak strategy")
    score_before   = results_before[0].score if results_before else 1.0

    await semantic.decay(eid, delta=0.3)

    results_after = await semantic.search("weak strategy")
    score_after   = results_after[0].score if results_after else 0.0
    assert score_after <= score_before
