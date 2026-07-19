"""
Experiment scenarios – inject controlled failures for benchmarking.

Each scenario patches tool failure rates, runs N tasks, then reports metrics.
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Callable

import structlog

from core.graph.workflow import run_task
from experiments.metrics import ExperimentResult, RunMetrics, extract_run_metrics
from tools.enterprise import (
    APIClientTool, DatabaseQueryTool, FileProcessorTool,
    NotifierTool, WebSearchTool,
)

log = structlog.get_logger(__name__)

# ── Example objectives to rotate across runs ───────────────────────────────────

SAMPLE_OBJECTIVES = [
    "Search for recent AI research papers and summarise the findings.",
    "Query the user database for inactive accounts and send a notification.",
    "Fetch the latest sales report from the API and process it into a summary.",
    "Read the config file, validate its schema, and notify the ops team.",
    "Retrieve customer feedback from the database and generate a weekly digest.",
]


# ── Scenario Runner ────────────────────────────────────────────────────────────

class ScenarioRunner:
    def __init__(self, name: str, num_runs: int = 10) -> None:
        self.name     = name
        self.num_runs = num_runs

    async def run(
        self,
        inject_failure: Callable[[], None],
        restore: Callable[[], None],
        objectives: list[str] | None = None,
    ) -> ExperimentResult:
        objectives = objectives or SAMPLE_OBJECTIVES
        result     = ExperimentResult(scenario_name=self.name)

        inject_failure()
        log.info("scenario.start", name=self.name, runs=self.num_runs)

        for i in range(self.num_runs):
            objective  = objectives[i % len(objectives)]
            task_id    = str(uuid.uuid4())

            try:
                state = await run_task(task_id, objective, max_repairs=3)
                metrics = extract_run_metrics(state)
                result.runs.append(metrics)
                log.info(
                    "scenario.run_done",
                    run=i + 1,
                    status=metrics.status,
                    rr=round(metrics.repair_rate, 2),
                )
            except Exception as exc:
                log.error("scenario.run_failed", run=i + 1, error=str(exc))

        restore()
        log.info("scenario.complete", summary=result.summary())
        return result


# ── Pre-built Scenarios ────────────────────────────────────────────────────────

async def run_network_failure_scenario(num_runs: int = 10) -> ExperimentResult:
    """Simulate intermittent network failures (30% rate)."""
    def inject():
        APIClientTool.failure_rate = 0.3
        WebSearchTool.failure_rate = 0.3

    def restore():
        APIClientTool.failure_rate = 0.0
        WebSearchTool.failure_rate = 0.0

    return await ScenarioRunner("network_failure", num_runs).run(inject, restore)


async def run_database_failure_scenario(num_runs: int = 10) -> ExperimentResult:
    """Simulate database connection errors (40% rate)."""
    def inject():
        DatabaseQueryTool.failure_rate = 0.4

    def restore():
        DatabaseQueryTool.failure_rate = 0.0

    return await ScenarioRunner("database_failure", num_runs).run(inject, restore)


async def run_cascading_failure_scenario(num_runs: int = 10) -> ExperimentResult:
    """Simulate cascading failures across all tools (20% rate)."""
    tools = [WebSearchTool, DatabaseQueryTool, APIClientTool, FileProcessorTool, NotifierTool]

    def inject():
        for t in tools:
            t.failure_rate = 0.2

    def restore():
        for t in tools:
            t.failure_rate = 0.0

    return await ScenarioRunner("cascading_failure", num_runs).run(inject, restore)


async def run_all_scenarios(num_runs: int = 10) -> dict[str, dict]:
    """Run all benchmark scenarios and return a summary report."""
    scenarios = await asyncio.gather(
        run_network_failure_scenario(num_runs),
        run_database_failure_scenario(num_runs),
        run_cascading_failure_scenario(num_runs),
    )
    return {s.scenario_name: s.summary() for s in scenarios}
