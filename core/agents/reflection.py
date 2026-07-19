"""
Reflection Agent – performs deep introspection on failures.

This is the intellectual core of self-healing:
  1. Collects all available evidence about the failure
  2. Queries episodic memory for similar past failures
  3. Queries the knowledge graph for known patterns
  4. Asks the LLM for a structured root-cause hypothesis
  5. Scores confidence and recommends a repair strategy
"""
from __future__ import annotations

import json
from typing import Any

import structlog
from langchain_core.messages import HumanMessage, SystemMessage

from core.agents.base import BaseAgent
from core.agents.llm_factory import build_llm
from core.graph.state import Failure, FailureType, PlanStep, RepairStrategy

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """\
You are an expert root-cause analysis (RCA) agent embedded in a self-healing \
multi-agent system.

## Failure Evidence
Step:           {step_description}
Tool:           {tool}
Parameters:     {parameters}
Raw error:      {raw_error}
Classified as:  {failure_type} ({severity})

## Execution History (last 5 steps)
{history}

## Similar Past Failures (from episodic memory)
{episodic_context}

## Known Repair Patterns (from knowledge graph)
{kg_patterns}

## Your Task
Analyse this failure thoroughly and return a JSON object with exactly these keys:
  "root_cause"           – concise one-sentence root cause (<= 120 chars)
  "confidence"           – float 0.0–1.0  (how sure you are)
  "failure_category"     – one of {failure_types}
  "repair_strategy"      – one of {strategies}
  "repair_rationale"     – why this strategy addresses the root cause
  "modified_parameters"  – updated parameter dict if strategy is retry_modified, else null
  "fallback_tool"        – alternative tool name if strategy is fallback, else null
  "prevention_note"      – short note to prevent recurrence in future plans

Return ONLY the JSON object, no markdown fences.
"""


class ReflectionAgent(BaseAgent):
    """
    Stateless agent that produces a structured RCA response.
    Instantiated fresh for each failure (cheap – no state).
    """

    def __init__(self) -> None:
        super().__init__("ReflectionAgent")
        self._llm = build_llm(temperature=0.05)  # deterministic for RCA

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        failure : dict = context["failure"]
        step    : dict = context["step"]
        history : list = context.get("step_results", [])
        episodic: str  = context.get("episodic_context", "None available.")
        kg_pats : str  = context.get("kg_patterns",     "None available.")

        prompt = _SYSTEM_PROMPT.format(
            step_description = step.get("description", ""),
            tool             = step.get("tool", ""),
            parameters       = json.dumps(step.get("parameters", {}), indent=2),
            raw_error        = failure.get("raw_error", ""),
            failure_type     = failure.get("failure_type", FailureType.UNKNOWN.value),
            severity         = failure.get("severity", "medium"),
            history          = _format_history(history),
            episodic_context = episodic,
            kg_patterns      = kg_pats,
            failure_types    = [f.value for f in FailureType],
            strategies       = [s.value for s in RepairStrategy],
        )

        raw = await self._llm.ainvoke([
            SystemMessage(content=prompt),
            HumanMessage(content="Produce the RCA JSON now."),
        ])

        try:
            analysis = json.loads(raw.content)
        except json.JSONDecodeError:
            # Graceful degradation: extract JSON block if wrapped in prose
            analysis = _extract_json(raw.content)

        log.info(
            "reflection.rca",
            root_cause = analysis.get("root_cause", "")[:80],
            confidence = analysis.get("confidence"),
            strategy   = analysis.get("repair_strategy"),
        )
        return {"rca": analysis}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _format_history(step_results: list[dict], last_n: int = 5) -> str:
    lines = []
    for r in step_results[-last_n:]:
        status = "✓" if r.get("success") else f"✗ {r.get('error', '')[:60]}"
        lines.append(f"  [{r['step_id']}] {status}")
    return "\n".join(lines) if lines else "  (no prior steps)"


def _extract_json(text: str) -> dict:
    """Try to salvage a JSON object from prose output."""
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return {
        "root_cause":          "Unable to parse LLM response",
        "confidence":          0.0,
        "failure_category":    FailureType.UNKNOWN.value,
        "repair_strategy":     RepairStrategy.RETRY.value,
        "repair_rationale":    "Fallback to retry due to parse error.",
        "modified_parameters": None,
        "fallback_tool":       None,
        "prevention_note":     "",
    }
