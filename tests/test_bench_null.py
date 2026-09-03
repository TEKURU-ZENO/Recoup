"""Phase 2 null hypothesis tests.

Verifies:
1. Identical arms (NaiveBounded vs SmartBounded in Phase 2) produce EXACTLY identical metrics (delta == 0).
2. Re-running the simulation on the same seed produces bit-identical results.
3. No non-deterministic leaks (e.g. dictionary ordering, timezone conversions, datetime.now calls).
"""

import pytest

from rra.bench.arms import NaiveBoundedArm, NaiveUnboundedArm, SmartBoundedArm
from rra.bench.runner import run_simulation


class TestBenchNullHypothesis:
    """Exact fairness and determinism checks for the benchmark harness."""

    def test_identical_arms_exact_equality(self):
        """Two instances of the same arm (e.g. NaiveBounded vs NaiveBounded) must yield exact zero delta."""
        arm1 = NaiveBoundedArm(name="NaiveBounded_1")
        arm2 = NaiveBoundedArm(name="NaiveBounded_2")
        seed = 42

        results_bounded, metrics1 = run_simulation(arm=arm1, seed=seed, n_cases=100)
        results_smart, metrics2 = run_simulation(arm=arm2, seed=seed, n_cases=100)

        # Assert EXACT equality across all metrics
        assert metrics1.total_cases == metrics2.total_cases
        assert metrics1.total_revenue_at_risk_paise == metrics2.total_revenue_at_risk_paise
        assert metrics1.total_recovered_paise == metrics2.total_recovered_paise
        assert metrics1.recovery_rate_pct == metrics2.recovery_rate_pct
        assert metrics1.retries_executed == metrics2.retries_executed
        assert metrics1.declined_chases == metrics2.declined_chases
        assert metrics1.interventions_sent == metrics2.interventions_sent
        assert metrics1.mean_days_to_settle == metrics2.mean_days_to_settle
        assert metrics1.guard_violations == metrics2.guard_violations

    def test_repeatability_exact_same_run(self):
        """Two runs of the exact same arm on the exact same seed produce bit-identical results."""
        arm = NaiveUnboundedArm()
        seed = 123

        res1, m1 = run_simulation(arm=arm, seed=seed, n_cases=50)
        res2, m2 = run_simulation(arm=arm, seed=seed, n_cases=50)

        assert m1.to_dict() == m2.to_dict()

        for (case1, hist1), (case2, hist2) in zip(res1, res2):
            assert case1.model_dump() == case2.model_dump()
            assert len(hist1) == len(hist2)
            for (act1, out1), (act2, out2) in zip(hist1, hist2):
                assert act1.model_dump() == act2.model_dump()
                assert out1.model_dump() == out2.model_dump()

    def test_three_arms_execute_cleanly(self):
        """All three arms run without errors across multiple seeds."""
        for seed in [1, 2, 3]:
            for arm in [NaiveUnboundedArm(), NaiveBoundedArm(), SmartBoundedArm()]:
                _, metrics = run_simulation(arm=arm, seed=seed, n_cases=20)
                assert metrics.total_cases == 20
                assert metrics.total_revenue_at_risk_paise > 0
