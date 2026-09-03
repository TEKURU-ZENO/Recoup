"""Deterministic policy engine.

Combines error taxonomy, state machine transitions, and compliance guardrails
to recommend the next action for a case.

NO LLM imports permitted. NO sim imports permitted.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from rra.domain.enums import ActionType, CaseStatus, ChannelType, EscalationLevel, FailureCode
from rra.domain.models import Action, Case, Outcome
from rra.engine.fsm import HIGH_VALUE_THRESHOLD_PAISE, initial_escalation_level
from rra.engine.guards import evaluate as evaluate_guards
from rra.engine.scheduler import next_retry_at


def next_action(
    case: Case,
    history: list[tuple[Action, Outcome]],
    now: datetime,
    use_smart_scheduling: bool = True,
    voice_enabled: bool = False,
) -> Action | None:
    """Determine the next recovery action for a case.

    Args:
        case: The recovery case state.
        history: Execution history of (Action, Outcome) tuples.
        now: Current simulation time.

    Returns:
        The next Action to take, or None if no action should be taken.
    """
    if case.status in (CaseStatus.SETTLED, CaseStatus.HALTED, CaseStatus.DECLINED):
        return None

    # Determine initial escalation level if still INGESTED
    if case.escalation_level == EscalationLevel.INGESTED:
        case.escalation_level = initial_escalation_level(case.failure_code)
        if case.escalation_level == EscalationLevel.TERMINAL_HALT:
            case.status = CaseStatus.HALTED
            return None

    executed = [act for act, _ in history if act.executed_at is not None]
    retries_count = sum(1 for a in executed if a.action_type == ActionType.BACKEND_RETRY)
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
    voice_count = sum(1 for a in executed if a.action_type == ActionType.VOICE_CALL)

    last_action_time = executed[-1].executed_at if executed else case.created_at

    proposed_action: Action | None = None

    # LEVEL 1: Smart_Retry
    if case.escalation_level == EscalationLevel.SMART_RETRY:
        # DECOUPLED DUNNING ARCHITECTURE:
        # For insufficient funds, decouple customer engagement from backend debit scheduling.
        # Dispatch an immediate digital nudge with payment link on Day 1 (t=0) while customer
        # intent is 100% fresh, while deferring automated auto-debits to the salary liquidity window.
        if (
            use_smart_scheduling
            and case.failure_code == FailureCode.INSUFFICIENT_FUNDS
            and nudges_count == 0
        ):
            proposed_action = Action(
                case_id=case.case_id,
                action_type=ActionType.SMS_NUDGE,
                channel=ChannelType.SMS,
                scheduled_at=now,
                rule_id="DECOUPLED_IMMEDIATE_NUDGE",
            )
        elif retries_count < 3:
            if use_smart_scheduling:
                smart_scheduled = next_retry_at(case, now)
                if smart_scheduled is None:
                    # Futile backend retry (e.g. card expired) -> jump to Digital_Nudge
                    case.escalation_level = EscalationLevel.DIGITAL_NUDGE
                else:
                    proposed_action = Action(
                        case_id=case.case_id,
                        action_type=ActionType.BACKEND_RETRY,
                        scheduled_at=max(now, smart_scheduled),
                        rule_id="SMART_RETRY_SCHEDULED",
                    )
            else:
                scheduled_at = max(now, last_action_time + timedelta(hours=24))
                proposed_action = Action(
                    case_id=case.case_id,
                    action_type=ActionType.BACKEND_RETRY,
                    scheduled_at=scheduled_at,
                    rule_id="RETRY_SCHEDULED",
                )
        else:
            case.escalation_level = EscalationLevel.DIGITAL_NUDGE

    # LEVEL 2: Digital_Nudge
    if case.escalation_level == EscalationLevel.DIGITAL_NUDGE:
        if nudges_count < 2:
            scheduled_at = max(now, last_action_time + timedelta(hours=48))
            
            # Select specific nudge channel / action type by failure code
            if case.failure_code == FailureCode.CARD_EXPIRED:
                act_type = ActionType.METHOD_SWITCH_LINK
                channel = ChannelType.WHATSAPP
                rule_id = "NUDGE_METHOD_SWITCH"
            elif case.failure_code == FailureCode.THREE_DS_DROPOFF:
                act_type = ActionType.FRICTION_REDUCTION_LINK
                channel = ChannelType.WHATSAPP
                rule_id = "NUDGE_FRICTION_REDUCTION"
            else:
                act_type = ActionType.SMS_NUDGE
                channel = ChannelType.SMS
                rule_id = "NUDGE_DIGITAL_REMINDER"

            proposed_action = Action(
                case_id=case.case_id,
                action_type=act_type,
                channel=channel,
                scheduled_at=scheduled_at,
                rule_id=rule_id,
            )
        else:
            # Advance to Voice Intercept if high value and voice enabled, else halt
            if voice_enabled and case.amount_due_paise >= HIGH_VALUE_THRESHOLD_PAISE and case.phone_number and not case.is_dnd:
                case.escalation_level = EscalationLevel.VOICE_INTERCEPT
            else:
                case.escalation_level = EscalationLevel.TERMINAL_HALT
                case.status = CaseStatus.HALTED
                return None

    # LEVEL 3: Voice_Intercept
    if case.escalation_level == EscalationLevel.VOICE_INTERCEPT:
        if voice_count < 1:
            scheduled_at = max(now, last_action_time + timedelta(hours=48))
            proposed_action = Action(
                case_id=case.case_id,
                action_type=ActionType.VOICE_CALL,
                channel=ChannelType.VOICE,
                scheduled_at=scheduled_at,
                rule_id="VOICE_INTERCEPT_CALL",
            )
        else:
            case.escalation_level = EscalationLevel.TERMINAL_HALT
            case.status = CaseStatus.HALTED
            return None

    if proposed_action is None:
        return None

    # Evaluate guards against proposed action
    decision = evaluate_guards(
        case=case,
        proposed_action=proposed_action,
        history=history,
        now=now,
    )

    if decision.allowed:
        proposed_action.rule_id = decision.rule_id
        return proposed_action

    # If action was deferred by TRAI_HOURS or COOLING_OFF, adjust scheduled_at
    if decision.deferred_until is not None:
        proposed_action.scheduled_at = decision.deferred_until
        proposed_action.rule_id = f"{decision.rule_id}_DEFERRED"
        return proposed_action

    # Hard guard violation block (OPT_OUT, REVOCATION, MAX_RETRIES, DND_SCRUB, etc.)
    return None
