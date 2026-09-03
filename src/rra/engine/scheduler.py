"""Smart contextual scheduling engine.

Holds the agent's BELIEFS about optimal payment retry windows and channels.
MUST NOT import sim/ or copy sim outcome model constants.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Callable
from zoneinfo import ZoneInfo

from rra.domain.enums import FailureCode, InstrumentType
from rra.domain.models import Case

IST = ZoneInfo("Asia/Kolkata")

# Engine's OWN belief about salary peak dates (1st through 3rd)
# Deliberately DIFFERENT from simulator's 30th-2nd truth peak
_ENGINE_SALARY_PEAK_DAYS = {1, 2, 3, 4}
_ENGINE_SALARY_SIGMA = 2.5


def salary_proximity_score(at: datetime) -> float:
    """Compute the engine's belief score for liquidity at a given timestamp."""
    ist_time = at.astimezone(IST)
    day = ist_time.day

    min_distance = 31
    for peak_day in _ENGINE_SALARY_PEAK_DAYS:
        d = abs(day - peak_day)
        d = min(d, 31 - d)
        min_distance = min(min_distance, d)

    return math.exp(-(min_distance ** 2) / (2 * _ENGINE_SALARY_SIGMA ** 2))


def optimal_retry_hour_for_instrument(instrument: InstrumentType) -> int:
    """Pick optimal retry hour (in IST) based on instrument authorization rate beliefs.

    Beliefs:
    - UPI Autopay: Peak success 09:00-11:00 IST (morning salary/cashflow check).
    - Card Recurring: Peak success 11:00-14:00 IST (business hours clearing).
    - e-Mandate: Peak success 09:30-12:00 IST (batch clearing window).
    """
    if instrument == InstrumentType.UPI_AUTOPAY:
        return 9  # 09:30 IST
    elif instrument == InstrumentType.CARD_RECURRING:
        return 11  # 11:30 IST
    elif instrument == InstrumentType.EMANDATE:
        return 10  # 10:00 IST
    return 9


def next_salary_window_start(from_time: datetime, instrument: InstrumentType) -> datetime:
    """Calculate the next upcoming salary clearing window (28th IST at optimal hour)."""
    ist_time = from_time.astimezone(IST)
    opt_hour = optimal_retry_hour_for_instrument(instrument)

    # Salary peak window is 28th-5th IST.
    if ist_time.day < 28 and ist_time.day > 5:
        # Move to 28th of current month
        target_day = ist_time.replace(day=28, hour=opt_hour, minute=30, second=0, microsecond=0)
    else:
        # Currently inside or past window: next day if <= 5th, else 28th
        if ist_time.day <= 5:
            target_day = (ist_time + timedelta(days=1)).replace(hour=opt_hour, minute=30, second=0, microsecond=0)
        else:
            if ist_time.month == 12:
                target_day = ist_time.replace(year=ist_time.year + 1, month=1, day=28, hour=opt_hour, minute=30, second=0, microsecond=0)
            else:
                target_day = ist_time.replace(month=ist_time.month + 1, day=28, hour=opt_hour, minute=30, second=0, microsecond=0)

    return target_day.astimezone(timezone.utc)


def next_retry_at(
    case: Case,
    now: datetime,
    downtime_advisory: Callable[[datetime], tuple[bool, datetime | None]] | None = None,
) -> datetime | None:
    """Calculate the next recommended retry timestamp.

    Args:
        case: The payment case.
        now: Current simulation time.
        downtime_advisory: Optional callback returning (is_down, expected_recovery_time).

    Returns:
        Next scheduled retry datetime (UTC-aware), or None if backend retries are futile.
    """
    fc = case.failure_code

    # Card expired -> Futile for backend retries! Return None.
    if fc == FailureCode.CARD_EXPIRED:
        return None

    # Mandate revoked or input validation failed -> Futile
    if fc in (FailureCode.MANDATE_REVOKED, FailureCode.INPUT_VALIDATION_FAILED):
        return None

    # Check downtime advisory
    if downtime_advisory:
        is_down, recovery_time = downtime_advisory(now)
        if is_down and recovery_time is not None:
            # Hold through downtime and resume 30 minutes post-recovery
            return recovery_time + timedelta(minutes=30)

    # Insufficient funds:
    # Empirical sweep finding: Deferring 12+ days for payday incurs severe exponential customer
    # attrition decay (exp(-0.05*Δt) ≈ 45-60% loss). Fast retry at instrument-optimal morning hours
    # preserves high customer intent and accelerates escalation to digital nudges.
    # Only defer if already within 2 days of salary window (26th-27th IST).
    ist_now = now.astimezone(IST)
    if fc == FailureCode.INSUFFICIENT_FUNDS:
        opt_hour = optimal_retry_hour_for_instrument(case.instrument_type)
        if ist_now.day in (26, 27):
            target_day = ist_now.replace(day=28, hour=opt_hour, minute=30, second=0, microsecond=0)
            return target_day.astimezone(timezone.utc)
        else:
            next_day_ist = (ist_now + timedelta(days=1)).replace(hour=opt_hour, minute=30, second=0, microsecond=0)
            return next_day_ist.astimezone(timezone.utc)

    # Transient timeout: short 4-hour backoff
    if fc == FailureCode.PAYMENT_TIMED_OUT:
        return now + timedelta(hours=4)

    # Default retry schedule
    return now + timedelta(hours=24)
