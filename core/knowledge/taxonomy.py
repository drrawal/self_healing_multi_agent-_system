"""
Failure taxonomy – canonical failure classification system.

Provides:
  - FailureTaxonomy dataclass with detection heuristics
  - classify_error() – maps a raw exception to a FailureType + severity
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from core.graph.state import FailureSeverity, FailureType


@dataclass(frozen=True)
class TaxonomyRule:
    """Maps error patterns to a failure type and severity."""
    failure_type : FailureType
    severity     : FailureSeverity
    patterns     : list[str]           # regex patterns to match against error text
    description  : str


# ── Rule Library ───────────────────────────────────────────────────────────────

TAXONOMY_RULES: list[TaxonomyRule] = [
    TaxonomyRule(
        failure_type = FailureType.NETWORK,
        severity     = FailureSeverity.HIGH,
        patterns     = [
            r"connection\s+refused", r"timeout", r"timed\s+out",
            r"connection\s+reset", r"network\s+unreachable", r"dns\s+resolution",
            r"ssl\s+error", r"certificate", r"unreachable",
        ],
        description  = "Network / connectivity failure",
    ),
    TaxonomyRule(
        failure_type = FailureType.TOOL,
        severity     = FailureSeverity.MEDIUM,
        patterns     = [
            r"tool\s+not\s+found", r"invalid\s+tool", r"tool\s+error",
            r"command\s+not\s+found", r"no\s+such\s+file", r"permission\s+denied",
            r"attribute.{0,1}error", r"type.{0,1}error",
        ],
        description  = "Tool invocation failure",
    ),
    TaxonomyRule(
        failure_type = FailureType.DATA,
        severity     = FailureSeverity.MEDIUM,
        patterns     = [
            r"validation.{0,1}error", r"schema.{0,1}error", r"json.{0,6}decode",
            r"parse.{0,1}error", r"key.{0,1}error", r"index.{0,1}error",
            r"value.{0,1}error", r"field.*required", r"field\s+required",
        ],
        description  = "Data validation / schema failure",
    ),
    TaxonomyRule(
        failure_type = FailureType.RESOURCE,
        severity     = FailureSeverity.CRITICAL,
        patterns     = [
            r"out\s+of\s+memory", r"disk\s+full", r"quota\s+exceeded",
            r"rate\s+limit", r"429", r"503", r"resource\s+exhausted",
            r"too\s+many\s+requests",
        ],
        description  = "Resource exhaustion / quota failure",
    ),
    TaxonomyRule(
        failure_type = FailureType.DEPENDENCY,
        severity     = FailureSeverity.HIGH,
        patterns     = [
            r"dependency\s+not\s+met", r"step\s+not",
            r"prerequisite", r"not\s+yet\s+available",
            r"not\s+yet\s+complete",
        ],
        description  = "Step dependency not satisfied",
    ),
    TaxonomyRule(
        failure_type = FailureType.LOGIC,
        severity     = FailureSeverity.MEDIUM,
        patterns     = [
            r"assertion\s+error", r"unexpected\s+output", r"invalid\s+result",
            r"logic\s+error", r"incorrect\s+response",
        ],
        description  = "Logic / reasoning failure",
    ),
]


def classify_error(
    error_text: str,
    tool_name : Optional[str] = None,
) -> tuple[FailureType, FailureSeverity]:
    """
    Classify a raw error string into a (FailureType, FailureSeverity) tuple.
    Falls back to UNKNOWN / MEDIUM when no rule matches.
    """
    lowered = error_text.lower()

    for rule in TAXONOMY_RULES:
        for pattern in rule.patterns:
            if re.search(pattern, lowered):
                return rule.failure_type, rule.severity

    return FailureType.UNKNOWN, FailureSeverity.MEDIUM
