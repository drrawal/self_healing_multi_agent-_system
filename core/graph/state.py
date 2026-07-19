"""
Core LangGraph state definitions.

All graph nodes receive and return an AgentState dict.
Immutability is enforced by returning new dicts (no in-place mutation).
"""
from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Annotated, Any, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


# ── Enumerations ───────────────────────────────────────────────────────────────

class AgentStatus(str, Enum):
    PLANNING    = "planning"
    EXECUTING   = "executing"
    FAILED      = "failed"
    REPAIRING   = "repairing"
    LEARNING    = "learning"
    COMPLETED   = "completed"
    ABORTED     = "aborted"


class FailureType(str, Enum):
    NETWORK     = "network"       # connectivity / timeout
    TOOL        = "tool"          # tool invocation error
    LOGIC       = "logic"         # incorrect reasoning / output
    DATA        = "data"          # validation / schema error
    RESOURCE    = "resource"      # CPU / memory / quota exhaustion
    DEPENDENCY  = "dependency"    # upstream step not complete
    UNKNOWN     = "unknown"


class FailureSeverity(str, Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class RepairStrategy(str, Enum):
    RETRY           = "retry"           # re-run same step unchanged
    RETRY_MODIFIED  = "retry_modified"  # retry with adjusted parameters
    FALLBACK        = "fallback"        # use alternative tool / approach
    REPLAN          = "replan"          # regenerate entire plan
    SKIP            = "skip"            # skip optional step
    ESCALATE        = "escalate"        # surface to human operator


# ── Value Objects (Pydantic) ───────────────────────────────────────────────────

class PlanStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str
    tool: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 2
    is_optional: bool = False
    fallback_tool: Optional[str] = None
    timeout_seconds: int = 60


class StepResult(BaseModel):
    step_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


class Failure(BaseModel):
    failure_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    step_id: str
    failure_type: FailureType = FailureType.UNKNOWN
    severity: FailureSeverity = FailureSeverity.MEDIUM
    description: str
    raw_error: str = ""
    timestamp: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    root_cause: Optional[str] = None
    root_cause_confidence: float = 0.0
    repair_strategy: Optional[RepairStrategy] = None
    repair_rationale: Optional[str] = None
    resolved: bool = False


class HealingMetrics(BaseModel):
    total_failures: int = 0
    total_repairs: int = 0
    successful_repairs: int = 0
    failed_repairs: int = 0
    mean_time_to_repair_ms: float = 0.0
    learning_updates: int = 0

    @property
    def repair_success_rate(self) -> float:
        if self.total_repairs == 0:
            return 0.0
        return self.successful_repairs / self.total_repairs


# ── LangGraph State ────────────────────────────────────────────────────────────

class AgentState(dict):
    """
    Typed dict for LangGraph.  All fields have defaults so partial
    updates via {**state, key: value} are always safe.

    Conventions:
      - Never mutate in-place; always return a new partial dict.
      - 'messages' is append-only (managed by add_messages reducer).
      - All timestamps are ISO-8601 UTC strings.
    """

    # ── identity ───
    task_id: str
    objective: str

    # ── plan ───
    plan: list[dict]               # list of PlanStep.model_dump()
    current_step_index: int

    # ── results ───
    step_results: list[dict]       # list of StepResult.model_dump()
    failures: list[dict]           # list of Failure.model_dump()

    # ── healing ───
    repair_count: int
    max_repairs: int
    status: str                    # AgentStatus value

    # ── context injected by memory / knowledge graph ───
    learned_context: dict          # relevant past strategies
    knowledge_snapshot: dict       # subgraph for current task

    # ── diagnostics ───
    start_time: float
    metrics: dict                  # HealingMetrics.model_dump()

    # ── conversation log (append-only, managed by add_messages) ───
    messages: Annotated[list[BaseMessage], add_messages]


def initial_state(task_id: str, objective: str, max_repairs: int = 3) -> dict:
    """Return a fresh AgentState with sensible defaults."""
    return {
        "task_id": task_id,
        "objective": objective,
        "plan": [],
        "current_step_index": 0,
        "step_results": [],
        "failures": [],
        "repair_count": 0,
        "max_repairs": max_repairs,
        "status": AgentStatus.PLANNING.value,
        "learned_context": {},
        "knowledge_snapshot": {},
        "start_time": time.time(),
        "metrics": HealingMetrics().model_dump(),
        "messages": [],
    }
