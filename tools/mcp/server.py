"""
MCP (Model Context Protocol) Server – exposes self-healing agent tools
over the MCP JSON-RPC interface.

This allows external MCP clients (e.g. Claude Desktop, VS Code Copilot)
to invoke enterprise tools and query system state through a standard protocol.
"""
from __future__ import annotations

import json
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

log = structlog.get_logger(__name__)

mcp_app = FastAPI(title="SelfHeal MCP Server", version="1.0.0")


# ── MCP Tool Catalogue ─────────────────────────────────────────────────────────

MCP_TOOLS = {
    "run_task": {
        "description": "Submit a task to the self-healing multi-agent workflow.",
        "parameters": {
            "type": "object",
            "properties": {
                "objective":    {"type": "string",  "description": "What to accomplish."},
                "max_repairs":  {"type": "integer", "description": "Max self-repair attempts.", "default": 3},
            },
            "required": ["objective"],
        },
    },
    "get_task_status": {
        "description": "Get the current status of a running or completed task.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "UUID of the task."},
            },
            "required": ["task_id"],
        },
    },
    "list_tools": {
        "description": "List all registered enterprise tools.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    "get_knowledge_stats": {
        "description": "Return statistics about the knowledge graph.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}


# ── MCP Protocol Endpoints ─────────────────────────────────────────────────────

@mcp_app.get("/mcp/tools")
async def list_mcp_tools() -> dict:
    return {"tools": [
        {"name": name, **spec}
        for name, spec in MCP_TOOLS.items()
    ]}


@mcp_app.post("/mcp/invoke")
async def invoke_mcp_tool(request: Request) -> JSONResponse:
    body: dict = await request.json()
    tool_name  = body.get("tool")
    params     = body.get("parameters", {})

    if tool_name not in MCP_TOOLS:
        return JSONResponse(
            status_code=404,
            content={"error": f"Unknown tool: {tool_name!r}"},
        )

    try:
        result = await _dispatch(tool_name, params)
        return JSONResponse(content={"result": result})
    except Exception as exc:
        log.error("mcp.invoke_error", tool=tool_name, error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)},
        )


async def _dispatch(tool_name: str, params: dict) -> Any:
    if tool_name == "run_task":
        import uuid
        from core.graph.workflow import run_task
        task_id   = str(uuid.uuid4())
        objective = params["objective"]
        max_rep   = int(params.get("max_repairs", 3))
        state     = await run_task(task_id, objective, max_rep)
        return {
            "task_id" : task_id,
            "status"  : state.get("status"),
            "repairs" : state.get("repair_count", 0),
            "failures": len(state.get("failures", [])),
        }

    if tool_name == "get_task_status":
        return {"message": "Retrieve from persistence layer (task_id lookup)."}

    if tool_name == "list_tools":
        from tools.registry import ToolRegistry
        return {"tools": ToolRegistry.instance().list_names()}

    if tool_name == "get_knowledge_stats":
        from core.knowledge.graph import KnowledgeGraph
        return KnowledgeGraph.instance().get_graph_stats()

    raise ValueError(f"No dispatcher for {tool_name!r}")
