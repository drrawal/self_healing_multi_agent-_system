"""
Knowledge Graph – NetworkX-based graph of agents, tools, failures, and repairs.

Node types:
  - agent       : an agent in the system
  - tool        : a callable tool
  - failure     : a failure instance (classified)
  - strategy    : a repair strategy
  - task        : a high-level objective pattern

Edge types:
  - uses_tool   : agent → tool
  - caused_by   : failure ← tool (the tool that failed)
  - repaired_by : failure → strategy (strategy that resolved it)
  - failed_with : task → failure_type (observed failure pattern)
  - succeeds_via: task → strategy (strategy that worked for this task type)

The graph is persisted as a pickle file for simplicity.
For production, replace with a proper graph DB (e.g. Neo4j).
"""
from __future__ import annotations

import pickle
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import networkx as nx
import structlog

from config.settings import get_settings
from core.graph.state import FailureType, RepairStrategy

log = structlog.get_logger(__name__)


class KnowledgeGraph:
    """
    Directed multigraph storing relationships between agents, tools,
    failures, and repair strategies.

    Singleton: call ``KnowledgeGraph.instance()``.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        settings   = get_settings()
        path       = db_path or settings.kg_db_path
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._g    = self._load()
        self._seed_baseline()

    @classmethod
    @lru_cache(maxsize=1)
    def instance(cls) -> "KnowledgeGraph":
        return cls()

    # ── Persistence ────────────────────────────────────────────────

    def _load(self) -> nx.DiGraph:
        if self._path.exists():
            try:
                with open(self._path, "rb") as fh:
                    g = pickle.load(fh)
                    log.info("kg.loaded", nodes=g.number_of_nodes(), edges=g.number_of_edges())
                    return g
            except Exception as exc:
                log.warning("kg.load_failed", error=str(exc))
        return nx.DiGraph()

    def save(self) -> None:
        with open(self._path, "wb") as fh:
            pickle.dump(self._g, fh)
        log.debug("kg.saved", nodes=self._g.number_of_nodes())

    # ── Write ──────────────────────────────────────────────────────

    def add_failure_pattern(
        self,
        tool          : str,
        failure_type  : str,
        repair_strategy: str,
        success       : bool,
        weight_delta  : float = 0.1,
    ) -> None:
        """
        Record that ``tool`` failed with ``failure_type`` and was handled
        by ``repair_strategy`` with outcome ``success``.
        """
        tool_node    = f"tool:{tool}"
        fail_node    = f"failure_type:{failure_type}"
        strategy_node= f"strategy:{repair_strategy}"

        for node, ntype in [
            (tool_node,     "tool"),
            (fail_node,     "failure_type"),
            (strategy_node, "strategy"),
        ]:
            if not self._g.has_node(node):
                self._g.add_node(node, type=ntype, label=node.split(":", 1)[1])

        # tool → failure type
        self._update_edge(tool_node, fail_node, "causes", weight_delta)

        # failure type → strategy
        edge_key = f"{failure_type}:{repair_strategy}"
        success_attr = "success_count" if success else "failure_count"
        if self._g.has_edge(fail_node, strategy_node):
            self._g[fail_node][strategy_node][success_attr] = (
                self._g[fail_node][strategy_node].get(success_attr, 0) + 1
            )
        else:
            self._g.add_edge(
                fail_node, strategy_node,
                type="repaired_by",
                success_count=1 if success else 0,
                failure_count=0 if success else 1,
                weight=weight_delta,
            )

        self.save()

    def record_task_outcome(
        self,
        task_type     : str,
        repair_strategy: str,
        success       : bool,
    ) -> None:
        task_node    = f"task:{task_type}"
        strategy_node= f"strategy:{repair_strategy}"

        for node, ntype in [(task_node, "task"), (strategy_node, "strategy")]:
            if not self._g.has_node(node):
                self._g.add_node(node, type=ntype, label=node.split(":", 1)[1])

        self._update_edge(
            task_node, strategy_node,
            "succeeds_via" if success else "fails_via",
            0.1 if success else -0.05,
        )
        self.save()

    # ── Query ──────────────────────────────────────────────────────

    def query_failure_patterns(
        self,
        failure_type : str,
        tool         : Optional[str] = None,
        top_k        : int = 3,
    ) -> str:
        """
        Return the top-k repair strategies for the given failure_type,
        sorted by success rate.
        """
        fail_node = f"failure_type:{failure_type}"
        if not self._g.has_node(fail_node):
            return ""

        candidates: list[tuple[float, str]] = []
        for _, strategy_node, data in self._g.out_edges(fail_node, data=True):
            s = data.get("success_count", 0)
            f = data.get("failure_count", 0)
            rate = s / (s + f) if (s + f) > 0 else 0.5
            strategy_name = strategy_node.split(":", 1)[1]
            candidates.append((rate, strategy_name))

        candidates.sort(reverse=True)
        if not candidates:
            return ""

        lines = [f"Known strategies for {failure_type}:"]
        for rate, strategy in candidates[:top_k]:
            lines.append(f"  {strategy}: {rate:.0%} success rate")
        return "\n".join(lines)

    def get_graph_stats(self) -> dict[str, Any]:
        return {
            "nodes"       : self._g.number_of_nodes(),
            "edges"       : self._g.number_of_edges(),
            "node_types"  : _count_by_attr(self._g, "type"),
        }

    # ── Helpers ────────────────────────────────────────────────────

    def _update_edge(
        self, src: str, dst: str, edge_type: str, delta: float
    ) -> None:
        if self._g.has_edge(src, dst):
            self._g[src][dst]["weight"] = (
                self._g[src][dst].get("weight", 0.0) + delta
            )
        else:
            self._g.add_edge(src, dst, type=edge_type, weight=delta)

    def _seed_baseline(self) -> None:
        """Pre-populate with known failure→strategy mappings."""
        defaults = [
            (FailureType.NETWORK.value,    RepairStrategy.RETRY.value,          True),
            (FailureType.NETWORK.value,    RepairStrategy.RETRY_MODIFIED.value,  True),
            (FailureType.TOOL.value,       RepairStrategy.FALLBACK.value,        True),
            (FailureType.DATA.value,       RepairStrategy.RETRY_MODIFIED.value,  True),
            (FailureType.RESOURCE.value,   RepairStrategy.RETRY.value,           False),
            (FailureType.RESOURCE.value,   RepairStrategy.ESCALATE.value,        True),
            (FailureType.LOGIC.value,      RepairStrategy.REPLAN.value,          True),
            (FailureType.DEPENDENCY.value, RepairStrategy.RETRY.value,           True),
        ]
        for ft, strategy, success in defaults:
            fail_node    = f"failure_type:{ft}"
            strategy_node= f"strategy:{strategy}"
            if not self._g.has_node(fail_node):
                self._g.add_node(fail_node, type="failure_type", label=ft)
            if not self._g.has_node(strategy_node):
                self._g.add_node(strategy_node, type="strategy", label=strategy)
            if not self._g.has_edge(fail_node, strategy_node):
                self._g.add_edge(
                    fail_node, strategy_node,
                    type="repaired_by",
                    success_count=3 if success else 1,
                    failure_count=1 if success else 3,
                    weight=0.3 if success else 0.1,
                )


def _count_by_attr(g: nx.DiGraph, attr: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for _, data in g.nodes(data=True):
        val = data.get(attr, "unknown")
        counts[val] = counts.get(val, 0) + 1
    return counts
