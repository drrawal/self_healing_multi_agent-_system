"""
Unit tests for the failure taxonomy classifier.
"""
from __future__ import annotations

import pytest

from core.knowledge.taxonomy import classify_error
from core.graph.state import FailureType, FailureSeverity


@pytest.mark.parametrize("error_text,expected_type", [
    ("connection timed out after 30s",           FailureType.NETWORK),
    ("Connection refused to 10.0.0.1:5432",      FailureType.NETWORK),
    ("ssl certificate verify failed",            FailureType.NETWORK),
    ("tool not found: web_scraper",              FailureType.TOOL),
    ("AttributeError: 'NoneType' has no attr",   FailureType.TOOL),
    ("ValidationError: field 'name' required",   FailureType.DATA),
    ("JSONDecodeError: Expecting value at line 1",FailureType.DATA),
    ("429 Too Many Requests",                    FailureType.RESOURCE),
    ("quota exceeded for project",               FailureType.RESOURCE),
    ("AssertionError: unexpected output value",  FailureType.LOGIC),
    ("step not yet complete",                    FailureType.DEPENDENCY),
    ("some completely unknown error xyz",        FailureType.UNKNOWN),
])
def test_classify_error_type(error_text: str, expected_type: FailureType):
    failure_type, _ = classify_error(error_text)
    assert failure_type == expected_type


def test_network_error_severity():
    _, severity = classify_error("connection timed out")
    assert severity == FailureSeverity.HIGH


def test_resource_error_severity():
    _, severity = classify_error("out of memory")
    assert severity == FailureSeverity.CRITICAL


def test_unknown_error_severity():
    _, severity = classify_error("something completely unrecognised abc123")
    assert severity == FailureSeverity.MEDIUM
