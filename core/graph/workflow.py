"""
LangGraph workflow assembly.

Graph topology:
                          ┌─────────────────────────────┐
                          ▼                             │
  START → planner → executor ──(fail)──► failure_detector
                       │                        │
                  (success/next)          root_cause_analyzer
                       │                        │
                     learner           plan_repairer ──(max)──► finalizer
                       │                        │
                   finalizer ◄──────────────── (retry) ──────► executor
"""
from __future__ import annotations

from functools import lru_cache

import structlog
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from core.graph.edges import (
    route_after_execution,
    route_after_learning,
    route_after_repair,
)
from core.graph.nodes import (
    executor_node,
    failure_detector_node,
    finalizer_node,
    learner_node,
    plan_repairer_node,
    planner_node,
    root_cause_analyzer_node,
)
from core.graph.state import AgentState

log = structlog.get_logger(__name__)


@lru_cache(maxsize=1)
def build_workflow():
    """
    Compile and return the LangGraph StateGraph.
    Cached so the graph is built once per process.
    """
    graph = StateGraph(AgentState)

    # ── Register nodes ─────────────────────────────────────────────
    graph.add_node("planner",             planner_node)
    graph.add_node("executor",            executor_node)
    graph.add_node("failure_detector",    failure_detector_node)
    graph.add_node("root_cause_analyzer", root_cause_analyzer_node)
    graph.add_node("plan_repairer",       plan_repairer_node)
    graph.add_node("learner",             learner_node)
    graph.add_node("finalizer",           finalizer_node)

    # ── Entry & static edges ───────────────────────────────────────
    graph.add_edge(START,                  "planner")
    graph.add_edge("planner",              "executor")
    graph.add_edge("failure_detector",     "root_cause_analyzer")
    graph.add_edge("root_cause_analyzer",  "plan_repairer")

    # ── Conditional edges ──────────────────────────────────────────
    graph.add_conditional_edges(
        "executor",
        route_after_execution,
        {
            "executor":         "executor",          # next step
            "failure_detector": "failure_detector",  # failure path
            "learner":          "learner",            # all steps done
        },
    )

    graph.add_conditional_edges(
        "plan_repairer",
        route_after_repair,
        {
            "executor":  "executor",   # retry repaired plan
            "finalizer": "finalizer",  # max repairs or escalate
        },
    )

    graph.add_conditional_edges(
        "learner",
        route_after_learning,
        {"finalizer": "finalizer"},
    )

    graph.add_edge("finalizer", END)

    # ── Compile with in-memory checkpointing ──────────────────────
    checkpointer = MemorySaver()
    compiled     = graph.compile(checkpointer=checkpointer)

    log.info("workflow.compiled")
    return compiled


async def run_task(task_id: str, objective: str, max_repairs: int = 3) -> dict:
    """
    High-level helper: run one task through the full healing workflow.

    Returns the final state dict.
    """
    from core.graph.state import initial_state

    workflow = build_workflow()
    state    = initial_state(task_id=task_id, objective=objective, max_repairs=max_repairs)
    config   = {"configurable": {"thread_id": task_id}}

    log.info("workflow.run", task_id=task_id, objective=objective[:80])

    final_state: dict = {}
    async for chunk in workflow.astream(state, config=config, stream_mode="values"):
        final_state = chunk

    log.info(
        "workflow.finished",
        task_id     = task_id,
        status      = final_state.get("status"),
        repairs     = final_state.get("repair_count", 0),
        failures    = len(final_state.get("failures", [])),
    )
    return final_state
