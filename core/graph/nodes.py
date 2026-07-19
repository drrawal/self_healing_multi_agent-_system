"""
Graph node implementations.

Each node is a pure async function:
    async def node(state: dict, config: RunnableConfig) -> dict

Nodes return *partial* state updates (only changed keys).
"""
from __future__ import annotations

import time
import uuid
from typing import Any

import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from core.graph.state import (
    AgentStatus,
    Failure,
    FailureSeverity,
    FailureType,
    HealingMetrics,
    PlanStep,
    RepairStrategy,
    StepResult,
)

log = structlog.get_logger(__name__)

# ── Private structured-output schemas ─────────────────────────────────────────
from pydantic import BaseModel, Field as _F  # noqa: E402


class _PlanStepRaw(BaseModel):
    description: str = ""
    tool: str = "noop"
    parameters: dict = _F(default_factory=dict)
    dependencies: list = _F(default_factory=list)
    is_optional: bool = False
    max_retries: int = 2
    fallback_tool: str | None = None


class _PlannerOutput(BaseModel):
    steps: list[_PlanStepRaw] = _F(default_factory=list)


class _RCAOutput(BaseModel):
    root_cause: str = ""
    confidence: float = 0.0
    repair_strategy: str = "retry"
    repair_rationale: str = ""
    modified_parameters: dict | None = None
    fallback_tool: str | None = None


# ── Lazy imports (break circular deps) ────────────────────────────────────────

def _get_llm():
    from core.agents.llm_factory import build_llm
    return build_llm()


def _get_tool_registry():
    from tools.registry import ToolRegistry
    return ToolRegistry.instance()


def _get_memory_manager():
    from core.memory.manager import MemoryManager
    return MemoryManager.instance()


def _get_knowledge_graph():
    from core.knowledge.graph import KnowledgeGraph
    return KnowledgeGraph.instance()


# ── Prompts ────────────────────────────────────────────────────────────────────

PLANNER_SYSTEM = """You are an enterprise task-planning agent.
Given an objective, produce a step-by-step execution plan.
Available tools: {tools}

Return a JSON object with key "steps", each step having:
  - description: what the step does
  - tool: one of the available tool names
  - parameters: dict of tool parameters
  - dependencies: list of step_ids this step depends on (empty for first step)
  - is_optional: true if skippable on failure
  - max_retries: 0-3

Prior successful strategies for similar tasks:
{learned_context}
"""

REFLECTION_SYSTEM = """You are a root-cause analysis (RCA) agent.
A step in an autonomous workflow has failed.

Failing step:   {step_description}
Tool called:    {tool}
Parameters:     {parameters}
Error:          {error}
Failure type:   {failure_type}

Recent execution history:
{history}

Known failure patterns from knowledge graph:
{kg_patterns}

Analyse the failure and return a JSON object:
  - root_cause: concise one-sentence root cause
  - confidence: 0.0 – 1.0
  - repair_strategy: one of {strategies}
  - repair_rationale: why this strategy addresses the root cause
  - modified_parameters: updated parameters if strategy is retry_modified (else null)
  - fallback_tool: alternative tool name if strategy is fallback (else null)
"""

REPLAN_SYSTEM = """You are a plan-repair agent.
The current execution plan failed beyond local repair.

Objective:    {objective}
Failed steps: {failed_steps}
Root causes:  {root_causes}
Available tools: {tools}

Generate a revised plan that avoids the identified failure modes.
Return the same JSON schema as the initial planner.
"""


# ── Node: planner ──────────────────────────────────────────────────────────────

async def planner_node(state: dict, config: RunnableConfig) -> dict:
    """Decomposes the objective into an ordered list of PlanSteps."""
    log.info("planner.start", task_id=state["task_id"], objective=state["objective"][:80])

    registry   = _get_tool_registry()
    memory_mgr = _get_memory_manager()

    available_tools   = registry.describe_all()
    learned_context   = await memory_mgr.recall_strategies(state["objective"])

    llm = _get_llm().with_structured_output(_PlannerOutput)

    response = await llm.ainvoke([
        SystemMessage(content=PLANNER_SYSTEM.format(
            tools=available_tools,
            learned_context=learned_context or "No prior context available.",
        )),
        HumanMessage(content=state["objective"]),
    ])

    plan = [PlanStep(
        description   = s.description,
        tool          = s.tool,
        parameters    = s.parameters,
        dependencies  = [str(d) for d in s.dependencies],
        is_optional   = s.is_optional,
        max_retries   = s.max_retries,
        fallback_tool = s.fallback_tool,
    ).model_dump() for s in response.steps]

    log.info("planner.done", steps=len(plan))
    return {
        "plan": plan,
        "current_step_index": 0,
        "status": AgentStatus.EXECUTING.value,
        "messages": [AIMessage(content=f"Plan created with {len(plan)} steps.")],
        "learned_context": learned_context,
    }


# ── Node: executor ─────────────────────────────────────────────────────────────

async def executor_node(state: dict, config: RunnableConfig) -> dict:
    """Executes the current plan step using the designated tool."""
    idx  = state["current_step_index"]
    plan = state["plan"]

    if idx >= len(plan):
        return {"status": AgentStatus.COMPLETED.value}

    step = PlanStep(**plan[idx])
    log.info("executor.step", step_id=step.step_id, tool=step.tool, index=idx)

    registry = _get_tool_registry()
    tool     = registry.get(step.tool)

    t0 = time.time()
    try:
        output = await tool.run_async(step.parameters)
        elapsed_ms = (time.time() - t0) * 1000

        result = StepResult(
            step_id          = step.step_id,
            success          = True,
            output           = output,
            execution_time_ms= elapsed_ms,
        ).model_dump()

        log.info("executor.success", step_id=step.step_id, ms=round(elapsed_ms))
        return {
            "step_results": state["step_results"] + [result],
            "current_step_index": idx + 1,
            "status": AgentStatus.EXECUTING.value,
        }

    except Exception as exc:
        elapsed_ms = (time.time() - t0) * 1000
        log.warning("executor.failure", step_id=step.step_id, error=str(exc))

        failure = Failure(
            step_id     = step.step_id,
            description = f"Step '{step.description}' failed: {exc}",
            raw_error   = str(exc),
        ).model_dump()

        # Bump retry_count on the plan step
        updated_plan = [dict(s) for s in plan]
        updated_plan[idx]["retry_count"] = step.retry_count + 1

        return {
            "plan": updated_plan,
            "step_results": state["step_results"] + [
                StepResult(
                    step_id          = step.step_id,
                    success          = False,
                    error            = str(exc),
                    execution_time_ms= elapsed_ms,
                ).model_dump()
            ],
            "failures": state["failures"] + [failure],
            "status": AgentStatus.FAILED.value,
        }


# ── Node: failure_detector ────────────────────────────────────────────────────

async def failure_detector_node(state: dict, config: RunnableConfig) -> dict:
    """Classifies the latest failure using the failure taxonomy."""
    from core.healing.detector import FailureDetector

    detector  = FailureDetector()
    failures  = state["failures"]
    if not failures:
        return {}

    latest_raw = failures[-1]
    classified = await detector.classify(latest_raw, state["step_results"])

    updated_failures = failures[:-1] + [classified]
    log.info(
        "detector.classified",
        failure_type=classified["failure_type"],
        severity=classified["severity"],
    )
    return {
        "failures": updated_failures,
        "status": AgentStatus.REPAIRING.value,
    }


# ── Node: root_cause_analyzer ─────────────────────────────────────────────────

async def root_cause_analyzer_node(state: dict, config: RunnableConfig) -> dict:
    """LLM-driven root cause analysis with knowledge graph augmentation."""
    kg      = _get_knowledge_graph()
    failure = Failure(**state["failures"][-1])
    idx     = state["current_step_index"]
    step    = PlanStep(**state["plan"][idx])

    kg_patterns = kg.query_failure_patterns(
        failure_type = failure.failure_type,
        tool         = step.tool,
    )
    history = _summarise_history(state["step_results"])

    llm = _get_llm().with_structured_output(_RCAOutput)

    response = await llm.ainvoke([
        SystemMessage(content=REFLECTION_SYSTEM.format(
            step_description = step.description,
            tool             = step.tool,
            parameters       = step.parameters,
            error            = failure.raw_error,
            failure_type     = failure.failure_type,
            history          = history,
            kg_patterns      = kg_patterns or "No known patterns.",
            strategies       = [s.value for s in RepairStrategy],
        )),
        HumanMessage(content="Analyse this failure and provide repair guidance."),
    ])

    updated_failure = {
        **state["failures"][-1],
        "root_cause":            response.root_cause,
        "root_cause_confidence": response.confidence,
        "repair_strategy":       response.repair_strategy or RepairStrategy.RETRY.value,
        "repair_rationale":      response.repair_rationale,
    }

    log.info(
        "rca.done",
        root_cause=updated_failure["root_cause"][:80],
        strategy=updated_failure["repair_strategy"],
        confidence=updated_failure["root_cause_confidence"],
    )

    return {
        "failures": state["failures"][:-1] + [updated_failure],
        "messages": [AIMessage(content=f"RCA: {updated_failure['root_cause']}")],
        "_rca_response": response.model_dump(),   # carry forward for repairer
    }


# ── Node: plan_repairer ────────────────────────────────────────────────────────

async def plan_repairer_node(state: dict, config: RunnableConfig) -> dict:
    """Applies the chosen repair strategy to the plan."""
    from core.healing.repairer import PlanRepairer

    repairer = PlanRepairer()
    result   = await repairer.repair(state)

    log.info(
        "repairer.done",
        strategy=result.get("applied_strategy"),
        repair_count=state["repair_count"] + 1,
    )

    return {
        **result,
        "repair_count": state["repair_count"] + 1,
        "status": AgentStatus.EXECUTING.value,
    }


# ── Node: learner ──────────────────────────────────────────────────────────────

async def learner_node(state: dict, config: RunnableConfig) -> dict:
    """
    Updates episodic memory and knowledge graph after each completed execution
    (successful or healed).  This closes the self-improvement loop.
    """
    from core.healing.learner import LearningEngine

    engine = LearningEngine()
    await engine.learn(state)

    metrics = _compute_metrics(state)
    log.info("learner.done", metrics=metrics)

    return {
        "status": AgentStatus.LEARNING.value,
        "metrics": metrics,
    }


# ── Node: finalizer ────────────────────────────────────────────────────────────

async def finalizer_node(state: dict, config: RunnableConfig) -> dict:
    """Produces a structured execution summary."""
    total_ms     = (time.time() - state["start_time"]) * 1000
    success_rate = _step_success_rate(state["step_results"])

    summary = (
        f"Task '{state['task_id']}' completed in {total_ms:.0f} ms. "
        f"Steps: {len(state['plan'])} | "
        f"Failures: {len(state['failures'])} | "
        f"Repairs: {state['repair_count']} | "
        f"Step success rate: {success_rate:.0%}"
    )
    log.info("finalizer", summary=summary)
    return {
        "status": AgentStatus.COMPLETED.value,
        "messages": [AIMessage(content=summary)],
    }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _summarise_history(step_results: list[dict], last_n: int = 5) -> str:
    rows = []
    for r in step_results[-last_n:]:
        status = "OK" if r["success"] else f"FAIL({r.get('error', '')[:60]})"
        rows.append(f"  {r['step_id']}: {status}")
    return "\n".join(rows) if rows else "No history."


def _step_success_rate(step_results: list[dict]) -> float:
    if not step_results:
        return 0.0
    successes = sum(1 for r in step_results if r["success"])
    return successes / len(step_results)


def _compute_metrics(state: dict) -> dict:
    failures  = state["failures"]
    results   = state["step_results"]
    healed    = sum(1 for f in failures if f.get("resolved"))
    total_ms  = (time.time() - state["start_time"]) * 1000

    return HealingMetrics(
        total_failures       = len(failures),
        total_repairs        = state["repair_count"],
        successful_repairs   = healed,
        failed_repairs       = state["repair_count"] - healed,
        mean_time_to_repair_ms = (
            total_ms / state["repair_count"] if state["repair_count"] else 0.0
        ),
    ).model_dump()
