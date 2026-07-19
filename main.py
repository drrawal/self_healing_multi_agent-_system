"""
Entry point for the Self-Healing Multi-Agent Framework.

Modes:
  api       – Start the REST API server
  run       – Run a single task from the command line
  experiment– Run the benchmark experiment suite
  demo      – Interactive Rich console demo
"""
from __future__ import annotations

import asyncio
import sys
import uuid

from config.logging_config import configure_logging


def _ensure_data_dir() -> None:
    from pathlib import Path
    Path("data").mkdir(exist_ok=True)


async def _run_single_task(objective: str) -> None:
    from rich.console import Console
    from rich.panel   import Panel
    from rich.table   import Table

    from core.graph.workflow import run_task

    console = Console()
    task_id = str(uuid.uuid4())

    console.print(Panel(
        f"[bold cyan]Objective:[/] {objective}\n"
        f"[bold cyan]Task ID  :[/] {task_id}",
        title="[bold]Self-Healing Multi-Agent Framework[/]",
        border_style="cyan",
    ))

    with console.status("[bold green]Running workflow…"):
        state = await run_task(task_id, objective, max_repairs=3)

    # ── Summary table ──
    table = Table(title="Execution Summary", show_header=True, header_style="bold magenta")
    table.add_column("Field",  style="cyan")
    table.add_column("Value",  style="white")

    table.add_row("Status",        state.get("status", "?"))
    table.add_row("Steps planned", str(len(state.get("plan", []))))
    table.add_row("Failures",      str(len(state.get("failures", []))))
    table.add_row("Repairs",       str(state.get("repair_count", 0)))

    metrics = state.get("metrics", {})
    table.add_row("Repair rate",   f"{metrics.get('successful_repairs', 0)}/{metrics.get('total_repairs', 0)}")

    console.print(table)

    if state.get("failures"):
        console.print("\n[bold yellow]Failures & Root Causes:[/]")
        for f in state["failures"]:
            console.print(
                f"  [red]•[/] [{f.get('failure_type', '?')}] "
                f"{f.get('root_cause', f.get('description', ''))[:100]} "
                f"→ repaired={f.get('resolved', False)}"
            )


async def _run_experiments(runs: int) -> None:
    from rich.console import Console
    from rich import print as rprint

    from experiments.runner import run_all_scenarios

    console = Console()
    console.print("[bold cyan]Running benchmark experiments…[/]")

    with console.status("[bold green]Executing scenarios (may take several minutes)…"):
        report = await run_all_scenarios(num_runs=runs)

    rprint(report)


def cli():
    """Console script entry point."""
    configure_logging()
    _ensure_data_dir()

    args = sys.argv[1:]
    mode = args[0] if args else "demo"

    if mode == "api":
        import uvicorn
        from config.settings import get_settings
        settings = get_settings()
        uvicorn.run(
            "api.app:app",
            host   = settings.api_host,
            port   = settings.api_port,
            reload = settings.api_debug,
        )

    elif mode == "run":
        objective = " ".join(args[1:]) or "Search for recent AI papers and send a summary notification."
        asyncio.run(_run_single_task(objective))

    elif mode == "experiment":
        runs = int(args[1]) if len(args) > 1 else 5
        asyncio.run(_run_experiments(runs))

    elif mode == "demo":
        objectives = [
            "Fetch the latest sales data from the database and generate a report.",
            "Search for security vulnerabilities in our codebase and notify the team.",
            "Process the uploaded CSV file and store the results in the database.",
        ]
        for obj in objectives:
            asyncio.run(_run_single_task(obj))

    else:
        print(f"Unknown mode: {mode!r}\nUsage: selfheal [api|run <objective>|experiment [runs]|demo]")
        sys.exit(1)


if __name__ == "__main__":
    cli()
