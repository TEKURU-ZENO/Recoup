"""Finite State Machine (FSM) for recovery lifecycle transitions.

Pure deterministic transitions between EscalationLevel states.
No LLM or simulator imports permitted.
"""

from __future__ import annotations

from rra.domain.enums import CaseStatus, EscalationLevel, FailureCode
from rra.domain.models import Case


class IllegalStateTransitionError(ValueError):
    """Raised when an illegal FSM state transition is attempted."""
    pass


# High-value threshold for Voice Intercept (₹5,000 = 500,000 paise)
HIGH_VALUE_THRESHOLD_PAISE = 500000


def initial_escalation_level(failure_code: FailureCode) -> EscalationLevel:
    """Determine starting escalation level based on diagnostic classification."""
    if failure_code in (FailureCode.MANDATE_REVOKED, FailureCode.INPUT_VALIDATION_FAILED):
        return EscalationLevel.TERMINAL_HALT
    elif failure_code in (FailureCode.CARD_EXPIRED, FailureCode.THREE_DS_DROPOFF):
        return EscalationLevel.DIGITAL_NUDGE
    else:
        # insufficient_funds, bank_downtime, payment_timed_out
        return EscalationLevel.SMART_RETRY


def transition(case: Case, event: str) -> Case:
    """Execute a state transition on a case.

    Events:
    - 'RETRY_EXHAUSTED': Smart_Retry -> Digital_Nudge
    - 'NUDGE_EXHAUSTED': Digital_Nudge -> Voice_Intercept (if high-value) or Terminal_Halt
    - 'P2P_CAPTURED': Voice_Intercept -> P2P_Scheduled
    - 'PAYMENT_SUCCESS': Any active state -> Settled
    - 'HARD_STOP': Any state -> Terminal_Halt (opt-out / revocation / dispute)
    - 'CALL_FAILED': Voice_Intercept -> Terminal_Halt

    Returns:
        Updated Case object.
    """
    current_level = case.escalation_level

    if current_level == EscalationLevel.TERMINAL_HALT:
        raise IllegalStateTransitionError("Cannot transition out of TERMINAL_HALT state.")

    if case.status == CaseStatus.SETTLED:
        raise IllegalStateTransitionError("Cannot transition a SETTLED case.")

    new_level = current_level
    new_status = case.status

    if event == "PAYMENT_SUCCESS":
        new_status = CaseStatus.SETTLED
    elif event == "HARD_STOP":
        new_level = EscalationLevel.TERMINAL_HALT
        new_status = CaseStatus.HALTED
    elif event == "RETRY_EXHAUSTED":
        if current_level in (EscalationLevel.INGESTED, EscalationLevel.SMART_RETRY):
            new_level = EscalationLevel.DIGITAL_NUDGE
        else:
            raise IllegalStateTransitionError(f"Cannot process RETRY_EXHAUSTED from level {current_level}")
    elif event == "NUDGE_EXHAUSTED":
        if current_level == EscalationLevel.DIGITAL_NUDGE:
            # High-value accounts advance to Voice_Intercept, others halt
            if case.amount_due_paise >= HIGH_VALUE_THRESHOLD_PAISE and case.phone_number and not case.is_dnd:
                new_level = EscalationLevel.VOICE_INTERCEPT
            else:
                new_level = EscalationLevel.TERMINAL_HALT
                new_status = CaseStatus.HALTED
        else:
            raise IllegalStateTransitionError(f"Cannot process NUDGE_EXHAUSTED from level {current_level}")
    elif event == "P2P_CAPTURED":
        if current_level == EscalationLevel.VOICE_INTERCEPT:
            new_status = CaseStatus.P2P_SCHEDULED
        else:
            raise IllegalStateTransitionError(f"Cannot process P2P_CAPTURED from level {current_level}")
    elif event == "CALL_FAILED":
        if current_level == EscalationLevel.VOICE_INTERCEPT:
            new_level = EscalationLevel.TERMINAL_HALT
            new_status = CaseStatus.HALTED
        else:
            raise IllegalStateTransitionError(f"Cannot process CALL_FAILED from level {current_level}")
    else:
        raise IllegalStateTransitionError(f"Unknown FSM event: '{event}'")

    case.escalation_level = new_level
    case.status = new_status
    return case
