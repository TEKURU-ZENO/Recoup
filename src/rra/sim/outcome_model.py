"""Outcome model — the sealed ground truth oracle.

Computes P(success | failure_code, action_type, timestamp) and resolves
actions into Outcome objects using a provided uniform draw.

This module defines the TRUTH. The engine/scheduler.py holds the agent's
BELIEFS. They must use different parameters. If you copy these constants
into the scheduler, you are grading your own homework.

All probability constants are documented in docs/assumptions.md.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from rra.domain.enums import ActionType, FailureCode
from rra.domain.models import Case, Outcome, _new_id
from rra.sim.downtime import DowntimeCalendar

IST = ZoneInfo("Asia/Kolkata")

# ---------------------------------------------------------------------------
# Probability constants — every one documented in docs/assumptions.md
# ---------------------------------------------------------------------------

# Salary proximity: Gaussian kernel peaked on 30th-2nd
# The SIMULATOR peaks on 30th-2nd. The ENGINE (scheduler.py) should
# use a DIFFERENT peak (e.g., 1st-3rd) to avoid grading your own homework.
_SALARY_PEAK_DAYS = {30, 31, 1, 2, 3, 4, 5}  # days of month (IST)
_SALARY_SIGMA = 3.0  # days [judgment]

# Attrition decay
_ATTRITION_LAMBDA = 0.05  # per day, ~14-day half-life [judgment]

# Base retry probability for insufficient_funds
_BASE_RETRY_PROB_INSUFFICIENT = 0.25  # [judgment]

# Bank downtime: probability when bank is up after outage
_POST_OUTAGE_RETRY_PROB = 0.70  # [judgment]

# Payment timed out: transient, retry usually works
_TIMEOUT_RETRY_PROB = 0.55  # [judgment]

# Link/nudge conversion rates (explicit, not "modest")
_NUDGE_CONVERSION_INSUFFICIENT_FUNDS = 0.12  # [judgment] - customer sees reminder
_NUDGE_CONVERSION_3DS_DROPOFF = 0.22  # [judgment] - friction-reduction link
_NUDGE_CONVERSION_CARD_EXPIRED = 0.18  # [judgment] - method-switch link
_NUDGE_CONVERSION_TIMEOUT = 0.10  # [judgment] - generic payment link

# Voice call P2P capture rates
_VOICE_P2P_CAPTURE_INSUFFICIENT_FUNDS = 0.55  # [judgment]
_VOICE_P2P_CAPTURE_3DS_DROPOFF = 0.40  # [judgment]
_VOICE_P2P_CAPTURE_CARD_EXPIRED = 0.45  # [judgment]

# P2P kept-rate: fraction of promises that result in actual payment
_P2P_KEPT_RATE = 0.68  # [judgment] - promises made vs payments landed


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _salary_proximity(at: datetime) -> float:
    """Gaussian kernel measuring proximity to salary credit dates.

    Peaked on the 30th through 5th of each month (IST).
    Returns a value in [0, 1] where 1.0 means right on a peak day.

    The peak uses the SIMULATOR's belief (30th-2nd center).
    The engine/scheduler.py must use its OWN, different parameters.
    """
    ist_time = at.astimezone(IST)
    day = ist_time.day

    # Find minimum circular distance to any peak day
    min_distance = 31  # larger than any month
    for peak_day in _SALARY_PEAK_DAYS:
        # Circular distance within a ~30-day month
        d = abs(day - peak_day)
        d = min(d, 31 - d)  # wrap around month boundary
        min_distance = min(min_distance, d)

    return math.exp(-(min_distance ** 2) / (2 * _SALARY_SIGMA ** 2))


def _attrition(elapsed_days: float) -> float:
    """Exponential decay with elapsed days since first failure.

    Models decreasing likelihood of recovery as time passes.
    Half-life ~14 days at lambda=0.05.
    """
    return math.exp(-_ATTRITION_LAMBDA * max(0.0, elapsed_days))


def _elapsed_days(case: Case, at: datetime) -> float:
    """Days elapsed since the case was created."""
    delta = at - case.created_at
    return max(0.0, delta.total_seconds() / 86400)


# ---------------------------------------------------------------------------
# Probability functions per failure_code x action_type
# ---------------------------------------------------------------------------

def _prob_insufficient_funds(
    case: Case, action_type: ActionType, at: datetime
) -> float:
    """Insufficient funds: responds to salary proximity and attrition."""
    elapsed = _elapsed_days(case, at)

    if action_type == ActionType.BACKEND_RETRY:
        return (
            _BASE_RETRY_PROB_INSUFFICIENT
            * _salary_proximity(at)
            * _attrition(elapsed)
        )
    elif action_type in (
        ActionType.SMS_NUDGE,
        ActionType.WHATSAPP_NUDGE,
        ActionType.PAYMENT_LINK,
    ):
        return _NUDGE_CONVERSION_INSUFFICIENT_FUNDS * _attrition(elapsed)
    elif action_type == ActionType.VOICE_CALL:
        # Voice captures P2P; actual payment depends on kept-rate
        return _VOICE_P2P_CAPTURE_INSUFFICIENT_FUNDS * _P2P_KEPT_RATE
    else:
        return 0.0


def _prob_bank_downtime(
    case: Case,
    action_type: ActionType,
    at: datetime,
    downtime_calendar: DowntimeCalendar | None = None,
) -> float:
    """Bank downtime: near zero inside outage, normal after recovery."""
    if action_type != ActionType.BACKEND_RETRY:
        return 0.0  # only backend retries work for infrastructure issues

    if downtime_calendar and downtime_calendar.is_down(at):
        return 0.02  # near zero but not exactly, small chance of partial recovery
    else:
        return _POST_OUTAGE_RETRY_PROB * _attrition(_elapsed_days(case, at))


def _prob_card_expired(
    case: Case, action_type: ActionType, at: datetime
) -> float:
    """Card expired: 0.0 for backend retry, non-zero only via method switch."""
    elapsed = _elapsed_days(case, at)

    if action_type == ActionType.BACKEND_RETRY:
        return 0.0  # can never succeed with expired card
    elif action_type in (
        ActionType.METHOD_SWITCH_LINK,
        ActionType.PAYMENT_LINK,
    ):
        return _NUDGE_CONVERSION_CARD_EXPIRED * _attrition(elapsed)
    elif action_type in (ActionType.SMS_NUDGE, ActionType.WHATSAPP_NUDGE):
        return _NUDGE_CONVERSION_CARD_EXPIRED * 0.8 * _attrition(elapsed)
    elif action_type == ActionType.VOICE_CALL:
        return _VOICE_P2P_CAPTURE_CARD_EXPIRED * _P2P_KEPT_RATE
    else:
        return 0.0


def _prob_3ds_dropoff(
    case: Case, action_type: ActionType, at: datetime
) -> float:
    """3DS drop-off: responds to friction-reduction link, not to retries."""
    elapsed = _elapsed_days(case, at)

    if action_type == ActionType.BACKEND_RETRY:
        return 0.03  # very low — same 3DS challenge will likely fail again
    elif action_type in (
        ActionType.FRICTION_REDUCTION_LINK,
        ActionType.PAYMENT_LINK,
    ):
        return _NUDGE_CONVERSION_3DS_DROPOFF * _attrition(elapsed)
    elif action_type in (ActionType.SMS_NUDGE, ActionType.WHATSAPP_NUDGE):
        return _NUDGE_CONVERSION_3DS_DROPOFF * 0.7 * _attrition(elapsed)
    elif action_type == ActionType.VOICE_CALL:
        return _VOICE_P2P_CAPTURE_3DS_DROPOFF * _P2P_KEPT_RATE
    else:
        return 0.0


def _prob_mandate_revoked(
    case: Case, action_type: ActionType, at: datetime
) -> float:
    """Mandate revoked: 0.0 for everything, permanently."""
    return 0.0


def _prob_payment_timed_out(
    case: Case, action_type: ActionType, at: datetime
) -> float:
    """Payment timed out: transient, retry works."""
    elapsed = _elapsed_days(case, at)

    if action_type == ActionType.BACKEND_RETRY:
        return _TIMEOUT_RETRY_PROB * _attrition(elapsed)
    elif action_type in (
        ActionType.SMS_NUDGE,
        ActionType.WHATSAPP_NUDGE,
        ActionType.PAYMENT_LINK,
    ):
        return _NUDGE_CONVERSION_TIMEOUT * _attrition(elapsed)
    else:
        return 0.0


def _prob_input_validation_failed(
    case: Case, action_type: ActionType, at: datetime
) -> float:
    """Input validation failed: system issue, nothing automated helps."""
    return 0.0


# Dispatch table
_PROB_DISPATCH: dict[
    FailureCode,
    type[...],  # actually callable, typed loosely for clarity
] = {
    FailureCode.INSUFFICIENT_FUNDS: _prob_insufficient_funds,
    FailureCode.BANK_DOWNTIME: _prob_bank_downtime,
    FailureCode.CARD_EXPIRED: _prob_card_expired,
    FailureCode.THREE_DS_DROPOFF: _prob_3ds_dropoff,
    FailureCode.MANDATE_REVOKED: _prob_mandate_revoked,
    FailureCode.PAYMENT_TIMED_OUT: _prob_payment_timed_out,
    FailureCode.INPUT_VALIDATION_FAILED: _prob_input_validation_failed,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def probability(
    case: Case,
    action_type: ActionType | str,
    at: datetime,
    downtime_calendar: DowntimeCalendar | None = None,
) -> float:
    """Compute P(success | failure_code, action_type, timestamp).

    Args:
        case: The recovery case.
        action_type: The type of action being taken.
        at: The timestamp of the action (UTC-aware).
        downtime_calendar: Optional downtime calendar for bank_downtime cases.

    Returns:
        A float in [0, 1].
    """
    if at.tzinfo is None:
        raise ValueError("Timestamp must be timezone-aware")

    action_type = ActionType(action_type) if isinstance(action_type, str) else action_type
    prob_fn = _PROB_DISPATCH.get(case.failure_code)

    if prob_fn is None:
        return 0.0

    # bank_downtime needs the calendar
    if case.failure_code == FailureCode.BANK_DOWNTIME:
        p = prob_fn(case, action_type, at, downtime_calendar)
    else:
        p = prob_fn(case, action_type, at)

    # Clamp to [0, 1]
    return max(0.0, min(1.0, p))


def draw(
    case: Case,
    action_type: ActionType | str,
    at: datetime,
    uniform: float,
    downtime_calendar: DowntimeCalendar | None = None,
    action_id: str | None = None,
) -> Outcome:
    """Resolve an action into an Outcome using a pre-drawn uniform.

    The uniform is generated by rng.draw_for() with common random numbers,
    ensuring fair comparison across benchmark arms.

    Args:
        case: The recovery case.
        action_type: The type of action being taken.
        at: The timestamp of the action.
        uniform: A uniform draw in [0, 1) from rng.draw_for().
        downtime_calendar: Optional downtime calendar.
        action_id: Optional deterministic action ID.

    Returns:
        An Outcome indicating success/failure and amount recovered.
    """
    action_type = ActionType(action_type) if isinstance(action_type, str) else action_type
    p = probability(case, action_type, at, downtime_calendar)
    success = uniform < p

    return Outcome(
        case_id=case.case_id,
        action_id=action_id or _new_id("act"),
        success=success,
        amount_recovered_paise=case.amount_due_paise if success else 0,
        timestamp=at,
    )
