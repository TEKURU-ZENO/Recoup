"""Tests for the simulator's outcome model.

Verifies probability curves, hard zeros, and the shape of the
salary proximity function.
"""

from datetime import datetime, timedelta, timezone

import pytest

from rra.domain.enums import ActionType, FailureCode, InstrumentType
from rra.domain.models import Case
from rra.sim.downtime import DowntimeCalendar
from rra.sim.outcome_model import probability, _salary_proximity, _attrition


def _utc(year=2026, month=4, day=1, hour=9):
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


def _make_case(failure_code: FailureCode, **overrides) -> Case:
    defaults = dict(
        case_id="case_test",
        subscription_id="sub_test",
        customer_name="Test User",
        amount_due_paise=100000,
        failure_code=failure_code,
        created_at=_utc(),
        updated_at=_utc(),
    )
    defaults.update(overrides)
    return Case(**defaults)


class TestHardZeros:
    """Probabilities that must be exactly zero, structurally."""

    def test_mandate_revoked_all_actions_all_times(self):
        """mandate_revoked: 0.0 for ALL action types at every timestamp."""
        case = _make_case(FailureCode.MANDATE_REVOKED)
        for action_type in ActionType:
            for day in range(1, 31):
                at = _utc(day=day, hour=12)
                p = probability(case, action_type, at)
                assert p == 0.0, (
                    f"mandate_revoked + {action_type} on day {day} = {p}, expected 0.0"
                )

    def test_card_expired_backend_retry_all_times(self):
        """card_expired + backend_retry: 0.0 at every timestamp."""
        case = _make_case(FailureCode.CARD_EXPIRED)
        for day in range(1, 31):
            at = _utc(day=day, hour=12)
            p = probability(case, ActionType.BACKEND_RETRY, at)
            assert p == 0.0, (
                f"card_expired + backend_retry on day {day} = {p}, expected 0.0"
            )

    def test_input_validation_failed_all_actions(self):
        """input_validation_failed: 0.0 for everything."""
        case = _make_case(FailureCode.INPUT_VALIDATION_FAILED)
        for action_type in ActionType:
            p = probability(case, action_type, _utc())
            assert p == 0.0


class TestProbabilityBounds:
    """All probabilities must be in [0, 1]."""

    def test_all_combinations_in_unit_interval(self):
        for fc in FailureCode:
            case = _make_case(fc)
            for at in ActionType:
                for day in [1, 5, 10, 15, 20, 25, 28, 30]:
                    for hour in [0, 6, 12, 18]:
                        try:
                            t = _utc(day=day, hour=hour)
                        except ValueError:
                            continue
                        p = probability(case, at, t)
                        assert 0.0 <= p <= 1.0, (
                            f"{fc} + {at} on day {day} h{hour}: p={p}"
                        )


class TestSalaryProximity:
    """Verify the shape of the salary proximity curve."""

    def test_peak_higher_than_trough(self):
        """The 1st of the month should have higher proximity than the 15th."""
        peak = _salary_proximity(_utc(day=1, hour=12))
        trough = _salary_proximity(_utc(day=15, hour=12))
        assert peak > trough, f"Peak {peak} should be > trough {trough}"

    def test_salary_days_high(self):
        """Days 30, 1, 2 should all have high proximity (> 0.5)."""
        for day in [1, 2, 3]:
            val = _salary_proximity(_utc(day=day, hour=12))
            assert val > 0.5, f"Day {day}: {val} should be > 0.5"

    def test_mid_month_low(self):
        """Days 10-20 should have low proximity (< 0.3)."""
        for day in [10, 12, 15, 18, 20]:
            val = _salary_proximity(_utc(day=day, hour=12))
            assert val < 0.3, f"Day {day}: {val} should be < 0.3"

    def test_proximity_in_unit_interval(self):
        for day in range(1, 29):
            val = _salary_proximity(_utc(day=day, hour=12))
            assert 0.0 <= val <= 1.0


class TestAttrition:
    """Verify the attrition decay function."""

    def test_zero_elapsed_is_one(self):
        assert _attrition(0.0) == 1.0

    def test_decays_over_time(self):
        assert _attrition(7.0) < _attrition(0.0)
        assert _attrition(14.0) < _attrition(7.0)
        assert _attrition(28.0) < _attrition(14.0)

    def test_half_life_approximately_14_days(self):
        val = _attrition(14.0)
        assert 0.45 < val < 0.55, f"14-day attrition = {val}, expected ~0.5"

    def test_never_negative(self):
        for d in range(0, 100):
            assert _attrition(float(d)) >= 0.0


class TestInsufficientFundsModel:
    """Verify insufficient_funds responds to salary proximity and attrition."""

    def test_salary_window_higher_than_midmonth(self):
        case = _make_case(FailureCode.INSUFFICIENT_FUNDS)
        p_salary = probability(
            case, ActionType.BACKEND_RETRY, _utc(day=1, hour=10)
        )
        p_mid = probability(
            case, ActionType.BACKEND_RETRY, _utc(day=15, hour=10)
        )
        assert p_salary > p_mid

    def test_attrition_reduces_probability(self):
        case_early = _make_case(
            FailureCode.INSUFFICIENT_FUNDS, created_at=_utc()
        )
        at_early = _utc(day=1, hour=10)  # 0 days elapsed
        at_late = _utc(month=4, day=20, hour=10)  # ~19 days elapsed
        p_early = probability(case_early, ActionType.BACKEND_RETRY, at_early)
        p_late = probability(case_early, ActionType.BACKEND_RETRY, at_late)
        assert p_early > p_late


class TestBankDowntimeModel:
    """Verify bank_downtime probabilities."""

    def test_near_zero_during_outage(self):
        """During a known outage, probability should be near zero."""
        start = _utc()
        calendar = DowntimeCalendar(seed=42, start=start)
        case = _make_case(FailureCode.BANK_DOWNTIME)

        # During scheduled maintenance (02:00 IST = 20:30 UTC previous day)
        # 02:00 IST = 20:30 UTC (IST is UTC+5:30)
        maintenance_time = datetime(2026, 3, 31, 20, 30, tzinfo=timezone.utc)
        p = probability(
            case, ActionType.BACKEND_RETRY, maintenance_time, calendar
        )
        assert p < 0.05  # near zero

    def test_normal_when_bank_is_up(self):
        """Outside outage windows, probability should be reasonable."""
        start = _utc()
        calendar = DowntimeCalendar(seed=42, start=start)
        case = _make_case(FailureCode.BANK_DOWNTIME)

        # 10:00 IST = 04:30 UTC (well outside maintenance)
        up_time = _utc(hour=5)  # 10:30 IST
        p = probability(case, ActionType.BACKEND_RETRY, up_time, calendar)
        assert p > 0.3  # should be reasonable


class TestCardExpiredModel:
    """Verify card_expired only responds to method switch, not retry."""

    def test_backend_retry_always_zero(self):
        case = _make_case(FailureCode.CARD_EXPIRED)
        for day in [1, 10, 20, 28]:
            p = probability(case, ActionType.BACKEND_RETRY, _utc(day=day))
            assert p == 0.0

    def test_method_switch_positive(self):
        case = _make_case(FailureCode.CARD_EXPIRED)
        p = probability(case, ActionType.METHOD_SWITCH_LINK, _utc())
        assert p > 0.0

    def test_voice_positive(self):
        case = _make_case(FailureCode.CARD_EXPIRED)
        p = probability(case, ActionType.VOICE_CALL, _utc())
        assert p > 0.0
