"""
Unit tests for the failure detector.
"""
from __future__ import annotations

import pytest

from core.healing.detector import FailureDetector
from core.graph.state import FailureType, FailureSeverity


@pytest.fixture
def detector():
    return FailureDetector()


@pytest.mark.asyncio
async def test_classify_network_failure(detector, sample_failure, sample_step):
    failure = {**sample_failure, "raw_error": "connection timed out after 30s"}
    step_results = [{"step_id": failure["step_id"], "success": False, "error": failure["raw_error"]}]
    enriched = await detector.classify(failure, step_results)
    assert enriched["failure_type"] == FailureType.NETWORK.value
    assert enriched["severity"] == FailureSeverity.HIGH.value


@pytest.mark.asyncio
async def test_classify_data_failure(detector, sample_failure):
    failure = {**sample_failure, "raw_error": "ValidationError: field 'email' required"}
    enriched = await detector.classify(failure, [])
    assert enriched["failure_type"] == FailureType.DATA.value


@pytest.mark.asyncio
async def test_classify_preserves_existing_fields(detector, sample_failure):
    enriched = await detector.classify(sample_failure, [])
    assert enriched["failure_id"] == sample_failure["failure_id"]
    assert enriched["step_id"]    == sample_failure["step_id"]
    assert enriched["description"]== sample_failure["description"]
