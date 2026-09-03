"""Tests for engine smart scheduler."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from rra.domain.enums import FailureCode, InstrumentType
from rra.domain.models import Case
from rra.engine.scheduler import next_retry_at, salary_proximity_score

IST = ZoneInfo("Asia/Kolkata")


def _utc_ist(year=2026, month=4, day=15, hour_ist=10) -> datetime:
    return datetime(year, month, day, hour_ist, 0, tzinfo=IST).astimezone(timezone.utc)


def _make_case(fc: FailureCode, **overrides) -> Case:
    defaults = dict(
        subscription_id="sub_sched",
        customer_name="Aarav",
        amount_due_paise=249900,
        failure_code=fc,
        instrument_type=InstrumentType.UPI_AUTOPAY,
        created_at=_utc_ist(),
        updated_at=_utc_ist(),
    )
    defaults.update(overrides)
    return Case(**defaults)


class TestScheduler:
    """Smart scheduler tests."""

    def test_adjacent_salary_window_aligns_to_28th(self):
        """Failure on April 26th (adjacent to payday) schedules into 28th IST salary window."""
        now = _utc_ist(month=4, day=26, hour_ist=10)
        case = _make_case(FailureCode.INSUFFICIENT_FUNDS)

        next_time = next_retry_at(case, now)
        assert next_time is not None

        next_ist = next_time.astimezone(IST)
        assert next_ist.day == 28

    def test_mid_month_insufficient_funds_fast_retry(self):
        """Mid-month (April 15th) failure executes fast retry at instrument-optimal hour to avoid attrition."""
        now = _utc_ist(month=4, day=15, hour_ist=10)
        case = _make_case(FailureCode.INSUFFICIENT_FUNDS, instrument_type=InstrumentType.UPI_AUTOPAY)

        next_time = next_retry_at(case, now)
        assert next_time is not None

        next_ist = next_time.astimezone(IST)
        assert next_ist.day == 16
        assert next_ist.hour == 9
        assert next_ist.minute == 30

    def test_card_expired_returns_none(self):
        """card_expired returns None so policy routes to method switch link."""
        now = _utc_ist()
        case = _make_case(FailureCode.CARD_EXPIRED)
        assert next_retry_at(case, now) is None

    def test_mandate_revoked_returns_none(self):
        now = _utc_ist()
        case = _make_case(FailureCode.MANDATE_REVOKED)
        assert next_retry_at(case, now) is None

    def test_payment_timed_out_short_backoff(self):
        now = _utc_ist()
        case = _make_case(FailureCode.PAYMENT_TIMED_OUT)
        next_time = next_retry_at(case, now)
        assert next_time is not None
        diff_hours = (next_time - now).total_seconds() / 3600.0
        assert diff_hours == 4.0

    def test_downtime_advisory_hold_and_resume(self):
        """Holds through bank downtime and resumes 30 mins after recovery."""
        now = _utc_ist()
        case = _make_case(FailureCode.BANK_DOWNTIME)

        # Mock downtime advisory
        recovery_time = now + datetime.resolution * 0 + pytest.importorskip("datetime").timedelta(hours=3)

        def mock_advisory(dt):
            return True, recovery_time

        next_time = next_retry_at(case, now, downtime_advisory=mock_advisory)
        assert next_time is not None
        assert next_time == recovery_time + pytest.importorskip("datetime").timedelta(minutes=30)
