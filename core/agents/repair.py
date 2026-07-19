"""
Repair Agent – translates a repair strategy into concrete plan mutations.

Strategies supported:
  RETRY           – re-execute unchanged (if retry_count < max_retries)
  RETRY_MODIFIED  – re-execute with LLM-adjusted parameters
  FALLBACK        – swap current tool for the fallback_tool
  REPLAN          – ask planner to regenerate from the failed step onward
  SKIP            – skip the optional step and advance
  ESCALATE        – mark as unrecoverable; surface to human
"""
from __future__ import annotations

import json
from typing import Any

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field as _F

from core.agents.base import BaseAgent
from core.agents.llm_factory import build_llm
from core.graph.state import AgentStatus, PlanStep, RepairStrategy

log = structlog.get_logger(__name__)


# ── Structured-output schema (replan) ────────────────────────────────────────

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


_REPLAN_PROMPT = """\
You are a plan-repair agent.

## Objective
{objective}

## Failed steps and root causes
{failed_summary}

## Available tools
{tools}

## Instructions
Generate a revised plan (JSON with key "steps") for the steps AFTER index {from_index}.
Avoid the failure modes described above.
Use the same step schema as the original planner.
"""


class RepairAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("RepairAgent")
        self._llm = build_llm()

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        state    : dict = context["state"]
        strategy : str  = context["strategy"]
        rca      : dict = context.get("rca", {})

        handler = {
            RepairStrategy.RETRY.value:          self._retry,
            RepairStrategy.RETRY_MODIFIED.value:  self._retry_modified,
            RepairStrategy.FALLBACK.value:         self._fallback,
            RepairStrategy.REPLAN.value:           self._replan,
            RepairStrategy.SKIP.value:             self._skip,
            RepairStrategy.ESCALATE.value:         self._escalate,
        }.get(strategy, self._retry)

        return await handler(state, rca)

    # ── Strategies ─────────────────────────────────────────────────

    async def _retry(self, state: dict, rca: dict) -> dict:
        idx  = state["current_step_index"]
        step = dict(state["plan"][idx])

        if step["retry_count"] >= step["max_retries"]:
            log.warning("repair.retry.exhausted", step_id=step["step_id"])
            return await self._escalate(state, rca)

        log.info("repair.retry", step_id=step["step_id"])
        updated_plan = list(state["plan"])
        updated_plan[idx] = step
        return {
            "plan": updated_plan,
            "applied_strategy": RepairStrategy.RETRY.value,
        }

    async def _retry_modified(self, state: dict, rca: dict) -> dict:
        idx             = state["current_step_index"]
        step            = dict(state["plan"][idx])
        new_params      = rca.get("modified_parameters") or step["parameters"]

        step["parameters"] = new_params
        updated_plan       = list(state["plan"])
        updated_plan[idx]  = step

        log.info("repair.retry_modified", step_id=step["step_id"], new_params=new_params)
        return {
            "plan": updated_plan,
            "applied_strategy": RepairStrategy.RETRY_MODIFIED.value,
        }

    async def _fallback(self, state: dict, rca: dict) -> dict:
        idx            = state["current_step_index"]
        step           = dict(state["plan"][idx])
        fallback_tool  = rca.get("fallback_tool") or step.get("fallback_tool")

        if not fallback_tool:
            log.warning("repair.fallback.no_tool", step_id=step["step_id"])
            return await self._retry(state, rca)

        step["tool"]       = fallback_tool
        step["retry_count"] = 0
        updated_plan        = list(state["plan"])
        updated_plan[idx]   = step

        log.info("repair.fallback", step_id=step["step_id"], fallback=fallback_tool)
        return {
            "plan": updated_plan,
            "applied_strategy": RepairStrategy.FALLBACK.value,
        }

    async def _replan(self, state: dict, rca: dict) -> dict:
        from tools.registry import ToolRegistry

        idx       = state["current_step_index"]
        registry  = ToolRegistry.instance()

        failed_summary = "\n".join(
            f"  Step {f['step_id']}: {f.get('root_cause', f['description'])}"
            for f in state["failures"]
        )

        llm  = self._llm.with_structured_output(_PlannerOutput)
        resp = await llm.ainvoke([
            SystemMessage(content=_REPLAN_PROMPT.format(
                objective     = state["objective"],
                failed_summary= failed_summary,
                tools         = registry.describe_all(),
                from_index    = idx,
            )),
            HumanMessage(content="Generate the revised plan now."),
        ])

        new_steps = [PlanStep(
            **{**s.model_dump(), "dependencies": [str(d) for d in s.dependencies]}
        ).model_dump() for s in resp.steps]
        updated_plan = state["plan"][:idx] + new_steps

        log.info("repair.replan", new_steps=len(new_steps))
        return {
            "plan": updated_plan,
            "current_step_index": idx,
            "applied_strategy": RepairStrategy.REPLAN.value,
        }

    async def _skip(self, state: dict, rca: dict) -> dict:
        idx  = state["current_step_index"]
        step = state["plan"][idx]

        if not step.get("is_optional", False):
            log.warning("repair.skip.mandatory", step_id=step["step_id"])
            return await self._escalate(state, rca)

        log.info("repair.skip", step_id=step["step_id"])
        return {
            "current_step_index": idx + 1,
            "applied_strategy": RepairStrategy.SKIP.value,
            "status": AgentStatus.EXECUTING.value,
        }

    async def _escalate(self, state: dict, rca: dict) -> dict:
        log.error(
            "repair.escalate",
            repair_count=state["repair_count"],
            failure_count=len(state["failures"]),
        )
        return {
            "status": AgentStatus.ABORTED.value,
            "applied_strategy": RepairStrategy.ESCALATE.value,
        }
