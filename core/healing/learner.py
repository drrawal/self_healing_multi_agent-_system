"""
Learning Engine – closes the self-improvement loop.

After each completed (or healed) execution the LearningEngine:
  1. Persists the episode to episodic memory
  2. Stores the repair strategy (with outcome) in semantic memory
  3. Updates the knowledge graph with failure→strategy outcome
  4. Reinforces or decays strategy scores in semantic memory
"""
from __future__ import annotations

import structlog

from config.settings import get_settings
from core.memory.manager import MemoryManager
from core.knowledge.graph import KnowledgeGraph

log = structlog.get_logger(__name__)


class LearningEngine:
    """
    Stateless service that processes a completed agent state and
    propagates lessons across all memory / knowledge stores.
    """

    def __init__(self) -> None:
        self._memory   = MemoryManager.instance()
        self._kg       = KnowledgeGraph.instance()
        self._settings = get_settings()

    async def learn(self, state: dict) -> None:
        """
        Main entry point called by the learner graph node.
        Idempotent: safe to call multiple times for the same state.
        """
        await self._record_episode(state)
        await self._learn_from_failures(state)
        log.info(
            "learner.complete",
            task_id     = state.get("task_id", ""),
            failures    = len(state.get("failures", [])),
            repair_count= state.get("repair_count", 0),
        )

    # ── Private ────────────────────────────────────────────────────

    async def _record_episode(self, state: dict) -> None:
        episode_id = await self._memory.record_execution(state)
        log.debug("learner.episode_stored", episode_id=episode_id)

    async def _learn_from_failures(self, state: dict) -> None:
        failures = state.get("failures", [])
        for failure in failures:
            strategy = failure.get("repair_strategy")
            if not strategy:
                continue

            tool         = _get_tool_for_failure(failure, state)
            failure_type = failure.get("failure_type", "unknown")
            resolved     = failure.get("resolved", False)
            lr           = self._settings.learning_rate

            # ── Semantic memory ──
            content = (
                f"Failure type '{failure_type}' on tool '{tool}' "
                f"repaired with '{strategy}'. "
                f"Root cause: {failure.get('root_cause', 'unknown')}. "
                f"Outcome: {'success' if resolved else 'failure'}."
            )
            entry_id = await self._memory.store_strategy(
                content      = content,
                failure_type = failure_type,
                tool         = tool,
                success      = resolved,
            )

            # Reinforce or decay
            if resolved:
                await self._memory.reinforce_strategy(entry_id)
            else:
                await self._memory.decay_strategy(entry_id)

            # ── Knowledge graph ──
            self._kg.add_failure_pattern(
                tool           = tool,
                failure_type   = failure_type,
                repair_strategy= strategy,
                success        = resolved,
                weight_delta   = lr if resolved else -lr * 0.5,
            )

        # Record task-level outcome
        if failures:
            task_type = _infer_task_type(state.get("objective", ""))
            all_resolved = all(f.get("resolved") for f in failures)
            last_strategy = failures[-1].get("repair_strategy", "unknown")
            self._kg.record_task_outcome(
                task_type      = task_type,
                repair_strategy= last_strategy,
                success        = all_resolved,
            )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_tool_for_failure(failure: dict, state: dict) -> str:
    step_id = failure.get("step_id", "")
    for step in state.get("plan", []):
        if step.get("step_id") == step_id:
            return step.get("tool", "unknown")
    return "unknown"


def _infer_task_type(objective: str) -> str:
    """Coarse-grain the objective to a reusable task type label."""
    objective_lower = objective.lower()
    keywords = {
        "search" : "information_retrieval",
        "query"  : "information_retrieval",
        "analyze": "analysis",
        "process": "data_processing",
        "send"   : "notification",
        "notify" : "notification",
        "report" : "reporting",
        "fetch"  : "data_retrieval",
    }
    for kw, task_type in keywords.items():
        if kw in objective_lower:
            return task_type
    return "general"
