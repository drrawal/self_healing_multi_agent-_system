"""
MCP (Model Context Protocol) Server – built with FastMCP.

Exposes self-healing agent tools over the standard MCP protocol so that
external clients (Claude Desktop, VS Code Copilot, etc.) can invoke them
directly via JSON-RPC / SSE transport.

Usage
-----
Standalone STDIO transport (for Claude Desktop / MCP Inspector):
    python -m tools.mcp.server

Mounted inside FastAPI (HTTP + SSE transport):
    app.mount("/mcp", mcp.http_app())
"""
from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastmcp import FastMCP
from pydantic import Field

log = structlog.get_logger(__name__)

# ── FastMCP instance ──────────────────────────────────────────────────────────

mcp = FastMCP(
    name="SH-MAS",
    version="1.0.0",
    instructions=(
        "Self-Healing Multi-Agent System – run tasks, inspect healing metrics, "
        "query the knowledge graph, and list enterprise tools."
    ),
)


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
async def run_task(
    objective: Annotated[str, Field(description="Task objective to accomplish", min_length=5)],
    max_repairs: Annotated[int, Field(description="Maximum self-repair attempts (0–10)", ge=0, le=10)] = 3,
) -> dict:
    """Submit an objective to the self-healing multi-agent workflow and return the result."""
    from core.graph.workflow import run_task as _run_task

    task_id = str(uuid.uuid4())
    log.info("mcp.run_task", task_id=task_id, objective=objective[:80])

    state = await _run_task(task_id=task_id, objective=objective, max_repairs=max_repairs)
    return {
        "task_id"      : task_id,
        "status"       : state.get("status"),
        "repair_count" : state.get("repair_count", 0),
        "failure_count": len(state.get("failures", [])),
        "metrics"      : state.get("metrics", {}),
    }


@mcp.tool()
async def get_task_status(
    task_id: Annotated[str, Field(description="UUID of the task to look up")],
) -> dict:
    """Retrieve a completed task execution record from the persistence layer."""
    from persistence.repositories import get_execution

    record = await get_execution(task_id)
    if record is None:
        return {"error": f"Task {task_id!r} not found."}

    return {
        "task_id"      : record.task_id,
        "objective"    : record.objective,
        "status"       : record.status,
        "repair_count" : record.repair_count,
        "failure_count": len(record.failures),
        "duration_ms"  : record.duration_ms,
        "metrics"      : record.metrics,
    }


@mcp.tool()
async def list_tools() -> dict:
    """List all enterprise tools registered in the tool registry."""
    from tools.registry import ToolRegistry

    registry = ToolRegistry.instance()
    return {"tools": registry.list_names()}


@mcp.tool()
async def get_knowledge_stats() -> dict:
    """Return node/edge counts and type breakdown for the knowledge graph."""
    from core.knowledge.graph import KnowledgeGraph

    return KnowledgeGraph.instance().get_graph_stats()


@mcp.tool()
async def get_healing_stats() -> dict:
    """Return aggregate healing metrics across all recorded task executions."""
    from persistence.repositories import get_healing_stats as _stats

    return await _stats()


# ── HTTP app (for FastAPI mount) ──────────────────────────────────────────────

def get_mcp_http_app():
    """Return an ASGI-compatible HTTP app for mounting inside FastAPI."""
    return mcp.http_app(path="/")


# ── Standalone entry-point (STDIO transport for MCP clients) ─────────────────

if __name__ == "__main__":
    mcp.run()  # defaults to STDIO transport

