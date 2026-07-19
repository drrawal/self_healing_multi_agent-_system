"""
Plan Repairer – applies the chosen repair strategy to the live plan.
Delegates strategy logic to RepairAgent.
"""
from __future__ import annotations

import structlog

from core.agents.repair import RepairAgent
from core.graph.state import RepairStrategy

log = structlog.get_logger(__name__)


class PlanRepairer:
    """
    Thin orchestration layer between the graph node and the RepairAgent.
    Adds pre/post logging and handles edge cases.
    """

    def __init__(self) -> None:
        self._agent = RepairAgent()

    async def repair(self, state: dict) -> dict:
        """
        Determine the repair strategy from the latest failure, invoke
        RepairAgent, and return the partial state update.
        """
        failures  = state.get("failures", [])
        if not failures:
            return {}

        failure  = failures[-1]
        strategy = failure.get("repair_strategy") or RepairStrategy.RETRY.value
        rca      = state.get("_rca_response", {})

        log.info(
            "repairer.start",
            strategy    = strategy,
            repair_count= state.get("repair_count", 0),
            failure_id  = failure.get("failure_id", ""),
        )

        result = await self._agent.execute({
            "state"   : state,
            "strategy": strategy,
            "rca"     : rca,
        })

        # Mark failure as resolved if not escalated
        applied = result.get("applied_strategy", strategy)
        if applied != RepairStrategy.ESCALATE.value:
            updated_failure = {**failure, "resolved": True}
            result["failures"] = failures[:-1] + [updated_failure]

        return result
