"""
Conditional edge routing logic for the LangGraph workflow.
All routing functions are pure (no side-effects, no I/O).
"""
from __future__ import annotations

from core.graph.state import AgentStatus, RepairStrategy


def route_after_planner(state: dict) -> str:
    """
    After the planner node:
      - If planning failed (ABORTED) → finalizer
      - Otherwise                    → executor
    """
    if state["status"] == AgentStatus.ABORTED.value:
        return "finalizer"
    return "executor"


def route_after_execution(state: dict) -> str:
    """
    After the executor node:
      - If a failure occurred  → failure_detector
      - If more steps remain   → executor (loop)
      - If plan is complete    → learner
    """
    if state["status"] == AgentStatus.FAILED.value:
        return "failure_detector"

    idx  = state["current_step_index"]
    plan = state["plan"]

    if idx < len(plan):
        return "executor"

    return "learner"


def route_after_repair(state: dict) -> str:
    """
    After the plan_repairer node:
      - If repair limit reached or strategy is ESCALATE → finalizer
      - Otherwise                                       → executor (retry)
    """
    if state["repair_count"] >= state["max_repairs"]:
        return "finalizer"

    latest_failure = state["failures"][-1] if state["failures"] else {}
    strategy = latest_failure.get("repair_strategy", RepairStrategy.RETRY.value)

    if strategy == RepairStrategy.ESCALATE.value:
        return "finalizer"

    return "executor"


def route_after_learning(state: dict) -> str:
    """After learner, always proceed to finalizer."""
    return "finalizer"
