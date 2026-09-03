"""Tests for FSM escalation state transitions."""

from datetime import datetime, timezone

import pytest

from rra.domain.enums import CaseStatus, EscalationLevel, FailureCode
from rra.domain.models import Case
from rra.engine.fsm import IllegalStateTransitionError, transition, initial_escalation_level


def _utc():
    return datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc)


def _make_case(level=EscalationLevel.INGESTED, status=CaseStatus.ACTIVE, amount=249900) -> Case:
    return Case(
        subscription_id="sub_123",
        customer_name="Aarav",
        amount_due_paise=amount,
        failure_code=FailureCode.INSUFFICIENT_FUNDS,
        escalation_level=level,
        status=status,
        phone_number="+919876543210",
        created_at=_utc(),
        updated_at=_utc(),
    )


class TestFSM:
    """State machine transitions testing."""

    def test_initial_escalation_levels(self):
        assert initial_escalation_level(FailureCode.INSUFFICIENT_FUNDS) == EscalationLevel.SMART_RETRY
        assert initial_escalation_level(FailureCode.BANK_DOWNTIME) == EscalationLevel.SMART_RETRY
        assert initial_escalation_level(FailureCode.CARD_EXPIRED) == EscalationLevel.DIGITAL_NUDGE
        assert initial_escalation_level(FailureCode.THREE_DS_DROPOFF) == EscalationLevel.DIGITAL_NUDGE
        assert initial_escalation_level(FailureCode.MANDATE_REVOKED) == EscalationLevel.TERMINAL_HALT

    def test_legal_transitions(self):
        case = _make_case(level=EscalationLevel.SMART_RETRY)
        
        # RETRY_EXHAUSTED -> DIGITAL_NUDGE
        c1 = transition(case, "RETRY_EXHAUSTED")
        assert c1.escalation_level == EscalationLevel.DIGITAL_NUDGE

        # NUDGE_EXHAUSTED -> VOICE_INTERCEPT (high value ₹5,000+)
        c1.amount_due_paise = 600000
        c2 = transition(c1, "NUDGE_EXHAUSTED")
        assert c2.escalation_level == EscalationLevel.VOICE_INTERCEPT

        # P2P_CAPTURED -> P2P_SCHEDULED status
        c3 = transition(c2, "P2P_CAPTURED")
        assert c3.status == CaseStatus.P2P_SCHEDULED

        # PAYMENT_SUCCESS -> SETTLED
        c4 = transition(c3, "PAYMENT_SUCCESS")
        assert c4.status == CaseStatus.SETTLED

    def test_illegal_transitions_raise(self):
        case = _make_case(level=EscalationLevel.TERMINAL_HALT)
        with pytest.raises(IllegalStateTransitionError):
            transition(case, "PAYMENT_SUCCESS")

        settled_case = _make_case(status=CaseStatus.SETTLED)
        with pytest.raises(IllegalStateTransitionError):
            transition(settled_case, "HARD_STOP")

        active_case = _make_case(level=EscalationLevel.INGESTED)
        with pytest.raises(IllegalStateTransitionError):
            transition(active_case, "P2P_CAPTURED")
