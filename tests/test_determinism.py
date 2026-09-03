"""Determinism tests — same seed must produce identical results.

This is a non-negotiable property. If any test here fails, the
benchmark's common-random-numbers mechanism is broken and the
comparison between arms is meaningless.
"""

from datetime import datetime, timezone

import pytest

from rra.domain.enums import ActionType, FailureCode
from rra.domain.models import Case
from rra.sim.portfolio import generate_portfolio
from rra.sim.rng import draw_for
from rra.sim.outcome_model import draw as outcome_draw, probability


def _utc(year=2026, month=4, day=1, hour=9):
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


class TestPortfolioDeterminism:
    """generate_portfolio must return identical batches for the same seed."""

    def test_same_seed_same_batch(self):
        batch_a = generate_portfolio(seed=42, n=50)
        batch_b = generate_portfolio(seed=42, n=50)
        assert len(batch_a) == len(batch_b) == 50
        for a, b in zip(batch_a, batch_b):
            assert a.case_id == b.case_id
            assert a.subscription_id == b.subscription_id
            assert a.customer_name == b.customer_name
            assert a.amount_due_paise == b.amount_due_paise
            assert a.failure_code == b.failure_code
            assert a.instrument_type == b.instrument_type
            assert a.phone_number == b.phone_number
            assert a.is_dnd == b.is_dnd
            assert a.language_preference == b.language_preference
            assert a.created_at == b.created_at

    def test_different_seed_different_batch(self):
        batch_a = generate_portfolio(seed=42, n=50)
        batch_b = generate_portfolio(seed=99, n=50)
        # At least some cases should differ
        differences = sum(
            1 for a, b in zip(batch_a, batch_b)
            if a.amount_due_paise != b.amount_due_paise
        )
        assert differences > 0

    def test_full_batch_determinism(self):
        """Full 215-case batch reproduces exactly."""
        batch_a = generate_portfolio(seed=1, n=215)
        batch_b = generate_portfolio(seed=1, n=215)
        for a, b in zip(batch_a, batch_b):
            assert a.model_dump() == b.model_dump()


class TestRNGDeterminism:
    """draw_for must return identical values for identical inputs."""

    def test_same_inputs_same_draw(self):
        d1 = draw_for(42, "case_abc", "backend_retry", 0)
        d2 = draw_for(42, "case_abc", "backend_retry", 0)
        assert d1 == d2  # exact equality, not approximate

    def test_different_seed_different_draw(self):
        d1 = draw_for(42, "case_abc", "backend_retry", 0)
        d2 = draw_for(99, "case_abc", "backend_retry", 0)
        assert d1 != d2

    def test_different_case_different_draw(self):
        d1 = draw_for(42, "case_abc", "backend_retry", 0)
        d2 = draw_for(42, "case_xyz", "backend_retry", 0)
        assert d1 != d2

    def test_different_action_type_different_draw(self):
        """Critical: retry and nudge draws must be independent."""
        d1 = draw_for(42, "case_abc", "backend_retry", 0)
        d2 = draw_for(42, "case_abc", "sms_nudge", 0)
        assert d1 != d2

    def test_different_ordinal_different_draw(self):
        d1 = draw_for(42, "case_abc", "backend_retry", 0)
        d2 = draw_for(42, "case_abc", "backend_retry", 1)
        assert d1 != d2

    def test_draw_in_unit_interval(self):
        """All draws must be in [0, 1)."""
        for seed in range(100):
            d = draw_for(seed, "case_test", "backend_retry", 0)
            assert 0.0 <= d < 1.0


class TestOutcomeDeterminism:
    """Outcome resolution must be deterministic given the same inputs."""

    def test_same_inputs_same_outcome(self):
        case = Case(
            case_id="case_det_test",
            subscription_id="sub_test",
            customer_name="Test User",
            amount_due_paise=100000,
            failure_code=FailureCode.INSUFFICIENT_FUNDS,
            created_at=_utc(),
            updated_at=_utc(),
        )
        uniform = 0.15
        at = _utc(hour=10)

        o1 = outcome_draw(case, ActionType.BACKEND_RETRY, at, uniform)
        o2 = outcome_draw(case, ActionType.BACKEND_RETRY, at, uniform)
        assert o1.success == o2.success
        assert o1.amount_recovered_paise == o2.amount_recovered_paise
