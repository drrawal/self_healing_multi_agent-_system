"""
Unit tests for the knowledge graph.
"""
from __future__ import annotations

import pytest

from core.knowledge.graph import KnowledgeGraph
from core.graph.state import FailureType, RepairStrategy


@pytest.fixture
def kg(tmp_path):
    """Fresh knowledge graph backed by a temp directory."""
    return KnowledgeGraph(db_path=str(tmp_path / "kg.pkl"))


def test_seed_baseline(kg):
    """The knowledge graph should come pre-seeded with baseline patterns."""
    patterns = kg.query_failure_patterns(FailureType.NETWORK.value)
    assert patterns, "Expected baseline patterns for network failures"


def test_add_failure_pattern(kg):
    kg.add_failure_pattern(
        tool           = "web_search",
        failure_type   = FailureType.NETWORK.value,
        repair_strategy= RepairStrategy.RETRY.value,
        success        = True,
    )
    patterns = kg.query_failure_patterns(FailureType.NETWORK.value, tool="web_search")
    assert "retry" in patterns.lower()


def test_record_task_outcome(kg):
    kg.record_task_outcome("information_retrieval", RepairStrategy.RETRY.value, success=True)
    stats = kg.get_graph_stats()
    assert stats["nodes"] > 0
    assert stats["edges"] > 0


def test_query_failure_patterns_empty(kg):
    result = kg.query_failure_patterns("nonexistent_failure_type_xyz")
    assert result == ""


def test_graph_stats(kg):
    stats = kg.get_graph_stats()
    assert "nodes" in stats
    assert "edges" in stats
    assert isinstance(stats["node_types"], dict)
