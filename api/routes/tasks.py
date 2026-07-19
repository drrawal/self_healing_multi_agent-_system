"""
Task routes – submit and inspect task executions.
"""
from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, HTTPException

from api.schemas.requests import RunTaskRequest, RunTaskResponse, TaskStatusResponse
from core.graph.workflow import run_task
from persistence.repositories import get_execution, list_executions, save_execution

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/", response_model=RunTaskResponse, status_code=201)
async def submit_task(body: RunTaskRequest) -> RunTaskResponse:
    """Submit a new task to the self-healing multi-agent workflow."""
    task_id = str(uuid.uuid4())
    log.info("api.task.submit", task_id=task_id, objective=body.objective[:80])

    final_state = await run_task(
        task_id     = task_id,
        objective   = body.objective,
        max_repairs = body.max_repairs,
    )

    await save_execution(final_state)

    messages = [
        m.content if hasattr(m, "content") else str(m)
        for m in final_state.get("messages", [])
        if hasattr(m, "content")
    ]

    return RunTaskResponse(
        task_id      = task_id,
        status       = final_state.get("status", "unknown"),
        repair_count = final_state.get("repair_count", 0),
        failure_count= len(final_state.get("failures", [])),
        metrics      = final_state.get("metrics", {}),
        messages     = messages[-5:],   # last 5 messages
    )


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task(task_id: str) -> TaskStatusResponse:
    """Retrieve a completed task execution by ID."""
    record = await get_execution(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id!r} not found.")

    return TaskStatusResponse(
        task_id      = record.task_id,
        objective    = record.objective,
        status       = record.status,
        repair_count = record.repair_count,
        step_count   = len(record.plan),
        failure_count= len(record.failures),
        duration_ms  = record.duration_ms,
        metrics      = record.metrics,
    )


@router.get("/", response_model=list[TaskStatusResponse])
async def list_tasks(limit: int = 20) -> list[TaskStatusResponse]:
    """List recent task executions."""
    records = await list_executions(limit=min(limit, 100))
    return [
        TaskStatusResponse(
            task_id      = r.task_id,
            objective    = r.objective,
            status       = r.status,
            repair_count = r.repair_count,
            step_count   = len(r.plan),
            failure_count= len(r.failures),
            duration_ms  = r.duration_ms,
            metrics      = r.metrics,
        )
        for r in records
    ]
