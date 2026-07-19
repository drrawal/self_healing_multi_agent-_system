"""
Integration tests for the metrics module.
"""
from __future__ import annotations

import time
import uuid

import pytest

from experiments.metrics import ExperimentResult, RunMetrics, extract_run_metrics


def make_state(status="completed", failures=None, repairs=0):
    return {
        "task_id"          : str(uuid.uuid4()),
        "objective"        : "Test objective",
        "status"           : status,
        "plan"             : [{"step_id": "s1"}, {"step_id": "s2"}],
        "step_results"     : [
            {"step_id": "s1", "success": True},
            {"step_id": "s2", "success": True},
        ],
        "failures"         : failures or [],
        "repair_count"     : repairs,
        "start_time"       : time.time() - 1.0,
        "metrics"          : {},
    }


def test_extract_run_metrics_no_failures():
    state   = make_state()
    metrics = extract_run_metrics(state)
    assert metrics.total_failures   == 0
    assert metrics.successful_repairs == 0
    assert metrics.repair_rate       == 1.0   # no failures = perfect rate


def test_extract_run_metrics_with_healed_failure():
    failure = {
        "failure_id"     : "f1",
        "failure_type"   : "network",
        "repair_strategy": "retry",
        "resolved"       : True,
    }
    state   = make_state(failures=[failure], repairs=1)
    metrics = extract_run_metrics(state)
    assert metrics.total_failures    == 1
    assert metrics.successful_repairs == 1
    assert metrics.repair_rate        == 1.0


def test_experiment_result_lpi_positive():
    """Learning Performance Index should be positive when later runs perform better."""
    result = ExperimentResult(scenario_name="test")

    # Early runs: poor repair rate (0.0 = no failures but also no repairs = 1.0... use failure)
    for _ in range(5):
        m = RunMetrics(
            task_id="t", objective="o", status="completed",
            total_steps=2, successful_steps=1,
            total_failures=2, successful_repairs=0,
        )
        result.runs.append(m)

    # Later runs: good repair rate
    for _ in range(5):
        m = RunMetrics(
            task_id="t", objective="o", status="completed",
            total_steps=2, successful_steps=2,
            total_failures=2, successful_repairs=2,
        )
        result.runs.append(m)

    assert result.learning_performance_index > 0


def test_experiment_result_summary_keys():
    result  = ExperimentResult(scenario_name="test")
    summary = result.summary()
    expected_keys = {
        "scenario", "num_runs", "plan_success_rate",
        "mean_repair_rate", "mean_mttr_ms",
        "mean_duration_ms", "learning_performance_index",
    }
    assert expected_keys.issubset(summary.keys())
