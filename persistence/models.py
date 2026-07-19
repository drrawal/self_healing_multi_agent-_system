"""
ORM models for persisting task executions and healing events.
"""
from __future__ import annotations

import time

from sqlalchemy import JSON, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from persistence.database import Base


class TaskExecution(Base):
    """Records every task run with its final state."""

    __tablename__ = "task_executions"

    id           : Mapped[int]   = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id      : Mapped[str]   = mapped_column(String(64),  nullable=False, index=True)
    objective    : Mapped[str]   = mapped_column(Text,        nullable=False)
    status       : Mapped[str]   = mapped_column(String(32),  nullable=False)
    plan         : Mapped[dict]  = mapped_column(JSON,        nullable=False, default=list)
    step_results : Mapped[dict]  = mapped_column(JSON,        nullable=False, default=list)
    failures     : Mapped[dict]  = mapped_column(JSON,        nullable=False, default=list)
    repair_count : Mapped[int]   = mapped_column(Integer,     nullable=False, default=0)
    metrics      : Mapped[dict]  = mapped_column(JSON,        nullable=False, default=dict)
    created_at   : Mapped[float] = mapped_column(Float,       nullable=False, default=time.time)
    duration_ms  : Mapped[float] = mapped_column(Float,       nullable=False, default=0.0)

    __table_args__ = (
        Index("ix_task_status", "task_id", "status"),
    )


class HealingEvent(Base):
    """Records individual healing attempts within a task execution."""

    __tablename__ = "healing_events"

    id              : Mapped[int]   = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id         : Mapped[str]   = mapped_column(String(64),  nullable=False, index=True)
    failure_id      : Mapped[str]   = mapped_column(String(32),  nullable=False)
    failure_type    : Mapped[str]   = mapped_column(String(32),  nullable=False)
    repair_strategy : Mapped[str]   = mapped_column(String(32),  nullable=False)
    root_cause      : Mapped[str]   = mapped_column(Text,        nullable=True)
    confidence      : Mapped[float] = mapped_column(Float,       nullable=False, default=0.0)
    resolved        : Mapped[bool]  = mapped_column(Integer,     nullable=False, default=0)
    created_at      : Mapped[float] = mapped_column(Float,       nullable=False, default=time.time)
