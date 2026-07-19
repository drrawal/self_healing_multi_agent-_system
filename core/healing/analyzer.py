"""
Root Cause Analyzer – orchestrates evidence gathering and delegates
LLM-based analysis to the ReflectionAgent.
"""
from __future__ import annotations

import structlog

from core.agents.reflection import ReflectionAgent
from core.memory.manager import MemoryManager
from core.knowledge.graph import KnowledgeGraph

log = structlog.get_logger(__name__)


class RootCauseAnalyzer:
    """
    Coordinates:
      1. Evidence collection (episodic memory + knowledge graph)
      2. ReflectionAgent invocation
      3. Annotating the failure dict with the RCA result
    """

    def __init__(self) -> None:
        self._agent   = ReflectionAgent()
        self._memory  = MemoryManager.instance()
        self._kg      = KnowledgeGraph.instance()

    async def analyze(self, state: dict) -> dict:
        """
        Performs RCA on the latest failure in ``state``.
        Returns a partial state update with the enriched failure.
        """
        failures = state.get("failures", [])
        if not failures:
            return {}

        failure = failures[-1]
        idx     = state.get("current_step_index", 0)
        plan    = state.get("plan", [])
        step    = plan[idx] if idx < len(plan) else {}

        # ── Gather context ─────────────────────────────────────────
        episodic_ctx = await self._memory.recall_episodes(
            query = f"{step.get('tool', '')} {failure.get('failure_type', '')}",
            top_k = 3,
        )
        kg_patterns = self._kg.query_failure_patterns(
            failure_type = failure.get("failure_type", "unknown"),
            tool         = step.get("tool"),
        )

        # ── Invoke Reflection Agent ────────────────────────────────
        rca_result = await self._agent.execute({
            "failure"         : failure,
            "step"            : step,
            "step_results"    : state.get("step_results", []),
            "episodic_context": episodic_ctx,
            "kg_patterns"     : kg_patterns,
        })
        rca = rca_result["rca"]

        # ── Annotate failure ───────────────────────────────────────
        enriched_failure = {
            **failure,
            "root_cause"           : rca.get("root_cause", ""),
            "root_cause_confidence": rca.get("confidence", 0.0),
            "repair_strategy"      : rca.get("repair_strategy"),
            "repair_rationale"     : rca.get("repair_rationale", ""),
        }

        log.info(
            "rca.complete",
            root_cause  = enriched_failure["root_cause"][:80],
            strategy    = enriched_failure["repair_strategy"],
            confidence  = enriched_failure["root_cause_confidence"],
        )

        return {
            "failures"    : failures[:-1] + [enriched_failure],
            "_rca_response": rca,   # carried forward by repair node
        }
