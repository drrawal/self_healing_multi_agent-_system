"""
Experiment metrics – measurable evaluation of self-healing effectiveness.

Key metrics for the research paper:
  - MTTR  (Mean Time To Repair)
  - RR    (Repair Rate = successful repairs / total failures)
  - LPI   (Learning Performance Index – improvement over runs)
  - FDR   (Failure Detection Rate – correct classifications)
  - PSR   (Plan Success Rate – tasks that complete without escalation)
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RunMetrics:
    """Metrics for a single task run."""
    task_id          : str
    objective        : str
    status           : str
    total_steps      : int
    successful_steps : int
    total_failures   : int
    successful_repairs: int
    repair_times_ms  : list[float] = field(default_factory=list)
    duration_ms      : float = 0.0
    failure_types    : list[str] = field(default_factory=list)

    @property
    def step_success_rate(self) -> float:
        return self.successful_steps / self.total_steps if self.total_steps else 0.0

    @property
    def repair_rate(self) -> float:
        return self.successful_repairs / self.total_failures if self.total_failures else 1.0

    @property
    def mttr_ms(self) -> float:
        return statistics.mean(self.repair_times_ms) if self.repair_times_ms else 0.0


@dataclass
class ExperimentResult:
    """Aggregated result across multiple runs of one experiment scenario."""
    scenario_name    : str
    runs             : list[RunMetrics] = field(default_factory=list)

    @property
    def num_runs(self) -> int:
        return len(self.runs)

    @property
    def plan_success_rate(self) -> float:
        """Fraction of runs that completed without ESCALATE."""
        completed = sum(1 for r in self.runs if r.status == "completed")
        return completed / self.num_runs if self.num_runs else 0.0

    @property
    def mean_repair_rate(self) -> float:
        rates = [r.repair_rate for r in self.runs]
        return statistics.mean(rates) if rates else 0.0

    @property
    def mean_mttr_ms(self) -> float:
        mttrs = [r.mttr_ms for r in self.runs if r.mttr_ms > 0]
        return statistics.mean(mttrs) if mttrs else 0.0

    @property
    def mean_duration_ms(self) -> float:
        durations = [r.duration_ms for r in self.runs]
        return statistics.mean(durations) if durations else 0.0

    @property
    def learning_performance_index(self) -> float:
        """
        LPI: measures whether later runs perform better than early runs.
        Positive LPI → system is learning.  Range: -1 to +1.
        """
        if len(self.runs) < 2:
            return 0.0
        mid  = len(self.runs) // 2
        early= statistics.mean(r.repair_rate for r in self.runs[:mid])
        late = statistics.mean(r.repair_rate for r in self.runs[mid:])
        return late - early   # +ve means improvement

    def summary(self) -> dict:
        return {
            "scenario"                 : self.scenario_name,
            "num_runs"                 : self.num_runs,
            "plan_success_rate"        : round(self.plan_success_rate, 3),
            "mean_repair_rate"         : round(self.mean_repair_rate, 3),
            "mean_mttr_ms"             : round(self.mean_mttr_ms, 1),
            "mean_duration_ms"         : round(self.mean_duration_ms, 1),
            "learning_performance_index": round(self.learning_performance_index, 3),
        }


def extract_run_metrics(state: dict) -> RunMetrics:
    """Build a RunMetrics object from a final agent state."""
    import time
    failures = state.get("failures", [])
    results  = state.get("step_results", [])

    return RunMetrics(
        task_id           = state["task_id"],
        objective         = state["objective"],
        status            = state.get("status", "unknown"),
        total_steps       = len(state.get("plan", [])),
        successful_steps  = sum(1 for r in results if r.get("success")),
        total_failures    = len(failures),
        successful_repairs= sum(1 for f in failures if f.get("resolved")),
        repair_times_ms   = [
            f.get("repair_time_ms", 0.0) for f in failures if f.get("resolved")
        ],
        duration_ms       = (time.time() - state.get("start_time", time.time())) * 1000,
        failure_types     = [f.get("failure_type", "unknown") for f in failures],
    )
