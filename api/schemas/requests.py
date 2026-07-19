"""
Request / response Pydantic schemas for the REST API.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class RunTaskRequest(BaseModel):
    objective  : str  = Field(..., min_length=5, description="Task objective to accomplish")
    max_repairs: int  = Field(default=3, ge=0, le=10)


class RunTaskResponse(BaseModel):
    task_id     : str
    status      : str
    repair_count: int
    failure_count: int
    metrics     : dict[str, Any]
    messages    : list[str]


class TaskStatusResponse(BaseModel):
    task_id     : str
    objective   : str
    status      : str
    repair_count: int
    step_count  : int
    failure_count: int
    duration_ms : float
    metrics     : dict[str, Any]


class HealingStatsResponse(BaseModel):
    total           : int
    resolved        : int
    resolution_rate : float
    by_failure_type : dict[str, Any]


class KnowledgeGraphStatsResponse(BaseModel):
    nodes     : int
    edges     : int
    node_types: dict[str, int]


class HealthResponse(BaseModel):
    status    : str = "ok"
    version   : str = "1.0.0"
    components: dict[str, str]
