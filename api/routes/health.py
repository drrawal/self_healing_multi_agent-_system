"""
Health and observability routes.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter

from api.schemas.requests import (
    HealingStatsResponse,
    HealthResponse,
    KnowledgeGraphStatsResponse,
)
from core.knowledge.graph import KnowledgeGraph
from persistence.repositories import get_healing_stats

log    = structlog.get_logger(__name__)
router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness / readiness probe."""
    components = {"api": "ok", "graph": "ok", "memory": "ok"}
    try:
        KnowledgeGraph.instance().get_graph_stats()
    except Exception:
        components["graph"] = "degraded"

    return HealthResponse(components=components)


@router.get("/healing/stats", response_model=HealingStatsResponse)
async def healing_stats() -> HealingStatsResponse:
    """Aggregate healing metrics from all recorded executions."""
    stats = await get_healing_stats()
    return HealingStatsResponse(**stats)


@router.get("/knowledge/stats", response_model=KnowledgeGraphStatsResponse)
async def knowledge_graph_stats() -> KnowledgeGraphStatsResponse:
    """Return knowledge graph statistics."""
    return KnowledgeGraphStatsResponse(**KnowledgeGraph.instance().get_graph_stats())
