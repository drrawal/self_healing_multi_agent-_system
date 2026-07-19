"""
Failure Detector – classifies a raw failure dict using the taxonomy.

Input : raw failure dict produced by executor_node
Output: enriched failure dict with failure_type and severity set
"""
from __future__ import annotations

import structlog

from core.knowledge.taxonomy import classify_error

log = structlog.get_logger(__name__)


class FailureDetector:
    """
    Stateless classifier.  Uses rule-based heuristics (taxonomy.py) for
    speed; can be augmented with an LLM call for edge cases.
    """

    async def classify(
        self,
        failure     : dict,
        step_results: list[dict],
    ) -> dict:
        """
        Enrich the failure dict with:
          - failure_type
          - severity
        """
        raw_error = failure.get("raw_error", failure.get("description", ""))
        step_id   = failure.get("step_id", "")

        # Grab the tool name from the latest failed step result
        tool_name = None
        for r in reversed(step_results):
            if r["step_id"] == step_id:
                break

        failure_type, severity = classify_error(raw_error, tool_name)

        enriched = {
            **failure,
            "failure_type": failure_type.value,
            "severity"    : severity.value,
        }
        log.debug(
            "detector.classified",
            step_id=step_id,
            type=failure_type.value,
            severity=severity.value,
        )
        return enriched
