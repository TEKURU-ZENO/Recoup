"""Benchmark harness package.

Public API:
- Arms: NaiveUnboundedArm, NaiveBoundedArm, SmartBoundedArm
- Runner: run_simulation
- Metrics: compute_metrics, ArmRunMetrics
- Report: run_benchmark, generate_report_markdown
"""

from rra.bench.arms import NaiveBoundedArm, NaiveUnboundedArm, SmartBoundedArm
from rra.bench.metrics import ArmRunMetrics, compute_metrics
from rra.bench.report import generate_report_markdown, run_benchmark
from rra.bench.runner import run_simulation

__all__ = [
    "ArmRunMetrics",
    "NaiveBoundedArm",
    "NaiveUnboundedArm",
    "SmartBoundedArm",
    "compute_metrics",
    "generate_report_markdown",
    "run_benchmark",
    "run_simulation",
]
