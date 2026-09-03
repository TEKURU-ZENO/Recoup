"""Regulatory and operational guardrails for bounded action execution.

Pure functions of (case, proposed_action, history, now).
No I/O or network calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from rra.domain.enums import ActionType, FailureCode
from rra.domain.models import Action, Case, Outcome

IST = ZoneInfo("Asia/Kolkata")


@dataclass
class GuardDecision:
    """Outcome of a guardrail evaluation."""

    allowed: bool
    rule_id: str
    reason: str
    deferred_until: datetime | None = None


def is_customer_contact(action_type: ActionType) -> bool:
    """Return True if action involves direct customer contact (SMS, WhatsApp, Voice)."""
    return action_type in (
        ActionType.SMS_NUDGE,
        ActionType.WHATSAPP_NUDGE,
        ActionType.VOICE_CALL,
        ActionType.PAYMENT_LINK,
        ActionType.METHOD_SWITCH_LINK,
        ActionType.FRICTION_REDUCTION_LINK,
    )


def evaluate(
    case: Case,
    proposed_action: Action,
    history: list[tuple[Action, Outcome]],
    now: datetime,
) -> GuardDecision:
    """Evaluate all guardrails against a proposed action.

    Args:
        case: The current case state.
        proposed_action: The proposed recovery action.
        history: Past executed actions and outcomes.
        now: Current simulation time (UTC-aware).

    Returns:
        GuardDecision indicating if allowed, rule_id, reason, and deferral time if applicable.
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    # 1. OPT_OUT rule: Hard stop if opted out
    if case.is_opted_out:
        return GuardDecision(
            allowed=False,
            rule_id="OPT_OUT",
            reason="Customer has explicitly opted out of communications.",
        )

    # 2. REVOCATION rule: Hard stop if mandate revoked
    if case.failure_code == FailureCode.MANDATE_REVOKED:
        return GuardDecision(
            allowed=False,
            rule_id="REVOCATION",
            reason="Mandate has been revoked by customer or issuing bank.",
        )

    # 3. INPUT_VALIDATION_FAILED: Hard stop
    if case.failure_code == FailureCode.INPUT_VALIDATION_FAILED:
        return GuardDecision(
            allowed=False,
            rule_id="UNRECOVERABLE_INPUT_ERROR",
            reason="System input validation failure cannot be automatically recovered.",
        )

    # Filter past executed actions
    executed = [act for act, _ in history if act.executed_at is not None]

    # 4. MAX_RETRIES rule: Max 3 backend retries per 30-day cycle
    if proposed_action.action_type == ActionType.BACKEND_RETRY:
        retries_count = sum(1 for a in executed if a.action_type == ActionType.BACKEND_RETRY)
        if retries_count >= 3:
            return GuardDecision(
                allowed=False,
                rule_id="MAX_RETRIES",
                reason=f"Maximum backend retries (3) reached for this cycle.",
            )

    # 5. MAX_NUDGES rule: Max 2 digital nudges
    if proposed_action.action_type in (
        ActionType.SMS_NUDGE,
        ActionType.WHATSAPP_NUDGE,
        ActionType.PAYMENT_LINK,
        ActionType.METHOD_SWITCH_LINK,
        ActionType.FRICTION_REDUCTION_LINK,
    ):
        nudges_count = sum(
            1
            for a in executed
            if a.action_type
            in (
                ActionType.SMS_NUDGE,
                ActionType.WHATSAPP_NUDGE,
                ActionType.PAYMENT_LINK,
                ActionType.METHOD_SWITCH_LINK,
                ActionType.FRICTION_REDUCTION_LINK,
            )
        )
        if nudges_count >= 2:
            return GuardDecision(
                allowed=False,
                rule_id="MAX_NUDGES",
                reason="Maximum digital nudges (2) reached.",
            )

    # 6. MAX_VOICE rule: Max 1 voice call
    if proposed_action.action_type == ActionType.VOICE_CALL:
        voice_count = sum(1 for a in executed if a.action_type == ActionType.VOICE_CALL)
        if voice_count >= 1:
            return GuardDecision(
                allowed=False,
                rule_id="MAX_VOICE",
                reason="Maximum voice call attempts (1) reached.",
            )

    # 7. DND_SCRUB rule: Block customer contacts if customer is DND-registered
    if is_customer_contact(proposed_action.action_type) and case.is_dnd:
        return GuardDecision(
            allowed=False,
            rule_id="DND_SCRUB",
            reason="Customer phone number is registered on DND preference registry.",
        )

    # 8. COOLING_OFF rule: 48h cooling-off between customer contacts ONLY
    # Silent backend retries DO NOT reset or check customer contact clock!
    if is_customer_contact(proposed_action.action_type):
        customer_contacts = [a for a in executed if is_customer_contact(a.action_type)]
        if customer_contacts:
            last_contact = max(customer_contacts, key=lambda a: a.executed_at)  # type: ignore
            next_allowed_contact = last_contact.executed_at + timedelta(hours=48)  # type: ignore
            if now < next_allowed_contact:
                return GuardDecision(
                    allowed=False,
                    rule_id="COOLING_OFF",
                    reason=f"Cooling-off period active until {next_allowed_contact.isoformat()}.",
                    deferred_until=next_allowed_contact,
                )

    # 9. TRAI_HOURS rule: 09:00-19:00 IST for customer contacts
    if is_customer_contact(proposed_action.action_type):
        ist_now = now.astimezone(IST)
        # Check if outside 09:00-19:00 IST window
        if ist_now.hour < 9 or (ist_now.hour >= 19 and (ist_now.hour > 19 or ist_now.minute > 0 or ist_now.second > 0)):
            # Calculate next 09:30 IST morning
            if ist_now.hour >= 19:
                next_morning_ist = (ist_now + timedelta(days=1)).replace(
                    hour=9, minute=30, second=0, microsecond=0
                )
            else:
                next_morning_ist = ist_now.replace(hour=9, minute=30, second=0, microsecond=0)
            
            deferred_utc = next_morning_ist.astimezone(timezone.utc)
            return GuardDecision(
                allowed=False,
                rule_id="TRAI_HOURS",
                reason="Customer contact outside TRAI allowed hours (09:00-19:00 IST). Deferring to 09:30 IST.",
                deferred_until=deferred_utc,
            )

    # All guards passed
    return GuardDecision(
        allowed=True,
        rule_id="GUARD_PERMITTED",
        reason="All operational and compliance guardrails passed.",
    )
