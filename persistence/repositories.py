"""
Repository layer – all DB interactions go through typed functions here.
No raw SQL or ORM logic in routes/services.
"""
from __future__ import annotations

import time

import structlog
from sqlalchemy import select

from persistence.database import get_session
from persistence.models import HealingEvent, TaskExecution

log = structlog.get_logger(__name__)


async def save_execution(state: dict) -> None:
    """Persist a completed task execution."""
    async with get_session() as session:
        record = TaskExecution(
            task_id     = state["task_id"],
            objective   = state["objective"],
            status      = state.get("status", "unknown"),
            plan        = state.get("plan", []),
            step_results= state.get("step_results", []),
            failures    = state.get("failures", []),
            repair_count= state.get("repair_count", 0),
            metrics     = state.get("metrics", {}),
            duration_ms = (time.time() - state.get("start_time", time.time())) * 1000,
        )
        session.add(record)

    # Persist healing events
    for failure in state.get("failures", []):
        await save_healing_event(state["task_id"], failure)


async def save_healing_event(task_id: str, failure: dict) -> None:
    async with get_session() as session:
        event = HealingEvent(
            task_id         = task_id,
            failure_id      = failure.get("failure_id", ""),
            failure_type    = failure.get("failure_type", "unknown"),
            repair_strategy = failure.get("repair_strategy", "unknown"),
            root_cause      = failure.get("root_cause"),
            confidence      = failure.get("root_cause_confidence", 0.0),
            resolved        = int(failure.get("resolved", False)),
        )
        session.add(event)


async def get_execution(task_id: str) -> TaskExecution | None:
    async with get_session() as session:
        result = await session.execute(
            select(TaskExecution).where(TaskExecution.task_id == task_id)
        )
        return result.scalar_one_or_none()


async def list_executions(limit: int = 50) -> list[TaskExecution]:
    async with get_session() as session:
        result = await session.execute(
            select(TaskExecution).order_by(TaskExecution.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())


async def get_healing_stats() -> dict:
    """Aggregate healing metrics across all recorded events."""
    async with get_session() as session:
        total_q = await session.execute(
            select(HealingEvent)
        )
        events = list(total_q.scalars().all())

    if not events:
        return {"total": 0, "resolved": 0, "resolution_rate": 0.0, "by_failure_type": {}}

    resolved = sum(1 for e in events if e.resolved)
    by_type  = {}
    for e in events:
        by_type.setdefault(e.failure_type, {"total": 0, "resolved": 0})
        by_type[e.failure_type]["total"] += 1
        if e.resolved:
            by_type[e.failure_type]["resolved"] += 1

    return {
        "total"          : len(events),
        "resolved"       : resolved,
        "resolution_rate": resolved / len(events),
        "by_failure_type": by_type,
    }
