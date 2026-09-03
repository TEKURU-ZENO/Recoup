"""Tests for domain types — models and enums."""

from datetime import datetime, timezone, timedelta

import pytest

from rra.domain.enums import (
    ActionType,
    CaseStatus,
    ChannelType,
    EscalationLevel,
    FailureCode,
    InstrumentType,
)
from rra.domain.models import Action, AuditRecord, Case, Outcome


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc(year=2026, month=4, day=1, hour=9, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _make_case(**overrides) -> Case:
    defaults = dict(
        subscription_id="sub_test123",
        customer_name="Aarav Sharma",
        amount_due_paise=249900,  # ₹2,499.00
        failure_code=FailureCode.INSUFFICIENT_FUNDS,
        created_at=_utc(),
        updated_at=_utc(),
    )
    defaults.update(overrides)
    return Case(**defaults)


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------

class TestEnums:
    def test_failure_code_values(self):
        assert FailureCode.INSUFFICIENT_FUNDS == "insufficient_funds"
        assert FailureCode.BANK_DOWNTIME == "bank_downtime"
        assert FailureCode.CARD_EXPIRED == "card_expired"
        assert FailureCode.THREE_DS_DROPOFF == "3ds_dropoff"
        assert FailureCode.MANDATE_REVOKED == "mandate_revoked"
        assert FailureCode.PAYMENT_TIMED_OUT == "payment_timed_out"
        assert FailureCode.INPUT_VALIDATION_FAILED == "input_validation_failed"

    def test_failure_code_count(self):
        assert len(FailureCode) == 7

    def test_escalation_levels(self):
        levels = list(EscalationLevel)
        assert len(levels) == 5
        assert EscalationLevel.INGESTED in levels
        assert EscalationLevel.TERMINAL_HALT in levels

    def test_case_status_values(self):
        assert CaseStatus.ACTIVE == "active"
        assert CaseStatus.SETTLED == "settled"
        assert CaseStatus.P2P_SCHEDULED == "p2p_scheduled"
        assert CaseStatus.HALTED == "halted"
        assert CaseStatus.DECLINED == "declined"

    def test_channel_types(self):
        assert len(ChannelType) == 5

    def test_action_types(self):
        assert ActionType.BACKEND_RETRY == "backend_retry"
        assert ActionType.METHOD_SWITCH_LINK == "method_switch_link"
        assert ActionType.HALT == "halt"
        assert len(ActionType) == 8

    def test_instrument_types(self):
        assert len(InstrumentType) == 3
        assert InstrumentType.UPI_AUTOPAY == "upi_autopay"


# ---------------------------------------------------------------------------
# Case model
# ---------------------------------------------------------------------------

class TestCase:
    def test_create_case(self):
        case = _make_case()
        assert case.subscription_id == "sub_test123"
        assert case.customer_name == "Aarav Sharma"
        assert case.amount_due_paise == 249900
        assert case.status == CaseStatus.ACTIVE
        assert case.escalation_level == EscalationLevel.INGESTED
        assert case.attempt_count == 0

    def test_paise_to_inr(self):
        case = _make_case(amount_due_paise=249900)
        assert case.amount_inr == 2499.0

    def test_single_paise(self):
        case = _make_case(amount_due_paise=1)
        assert case.amount_inr == 0.01

    def test_amount_must_be_positive(self):
        with pytest.raises(Exception):
            _make_case(amount_due_paise=0)

    def test_negative_amount_rejected(self):
        with pytest.raises(Exception):
            _make_case(amount_due_paise=-100)

    def test_naive_datetime_rejected(self):
        with pytest.raises(ValueError, match="Naive datetimes"):
            _make_case(created_at=datetime(2026, 4, 1, 9, 0))

    def test_case_id_prefix(self):
        case = _make_case()
        assert case.case_id.startswith("case_")

    def test_dnd_flag_default(self):
        case = _make_case()
        assert case.is_dnd is False

    def test_opted_out_default(self):
        case = _make_case()
        assert case.is_opted_out is False


# ---------------------------------------------------------------------------
# Action model
# ---------------------------------------------------------------------------

class TestAction:
    def test_create_action(self):
        action = Action(
            case_id="case_abc123",
            action_type=ActionType.BACKEND_RETRY,
            scheduled_at=_utc(),
        )
        assert action.action_id.startswith("act_")
        assert action.action_type == ActionType.BACKEND_RETRY
        assert action.channel is None
        assert action.result is None

    def test_action_with_channel(self):
        action = Action(
            case_id="case_abc123",
            action_type=ActionType.SMS_NUDGE,
            channel=ChannelType.SMS,
            scheduled_at=_utc(),
        )
        assert action.channel == ChannelType.SMS

    def test_naive_scheduled_at_rejected(self):
        with pytest.raises(ValueError, match="Naive datetimes"):
            Action(
                case_id="case_abc123",
                action_type=ActionType.BACKEND_RETRY,
                scheduled_at=datetime(2026, 4, 1),
            )


# ---------------------------------------------------------------------------
# Outcome model
# ---------------------------------------------------------------------------

class TestOutcome:
    def test_create_outcome(self):
        outcome = Outcome(
            case_id="case_abc123",
            action_id="act_def456",
            success=True,
            amount_recovered_paise=249900,
            timestamp=_utc(),
        )
        assert outcome.success is True
        assert outcome.amount_recovered_paise == 249900

    def test_failed_outcome(self):
        outcome = Outcome(
            case_id="case_abc123",
            action_id="act_def456",
            success=False,
            amount_recovered_paise=0,
            timestamp=_utc(),
        )
        assert outcome.success is False
        assert outcome.amount_recovered_paise == 0

    def test_negative_recovery_rejected(self):
        with pytest.raises(Exception):
            Outcome(
                case_id="case_abc123",
                action_id="act_def456",
                success=True,
                amount_recovered_paise=-100,
                timestamp=_utc(),
            )


# ---------------------------------------------------------------------------
# AuditRecord model
# ---------------------------------------------------------------------------

class TestAuditRecord:
    def test_create_audit_record(self):
        record = AuditRecord(
            subscription_id="sub_test123",
            actor="AGENT_POLICY_ENGINE",
            rule_triggered="RULE_LIQUIDITY_SYNC",
            inputs={"error_code": "insufficient_funds", "attempt": 1},
            execution_payload={"action": "SCHEDULE_RETRY"},
            compliance_check={"trai_hours": True, "dnd_scrub": True},
        )
        assert record.audit_id.startswith("aud_")
        assert record.previous_hash == "genesis"
        assert record.record_hash != ""

    def test_audit_record_is_frozen(self):
        record = AuditRecord(
            subscription_id="sub_test123",
            actor="AGENT_POLICY_ENGINE",
            rule_triggered="TEST_RULE",
        )
        with pytest.raises(Exception):
            record.actor = "TAMPERED"

    def test_hash_determinism(self):
        """Same inputs produce the same hash."""
        ts = _utc()
        kwargs = dict(
            audit_id="aud_fixed",
            timestamp_utc=ts,
            subscription_id="sub_test123",
            actor="AGENT_POLICY_ENGINE",
            rule_triggered="TEST_RULE",
            inputs={"k": "v"},
            previous_hash="genesis",
        )
        r1 = AuditRecord(**kwargs)
        r2 = AuditRecord(**kwargs)
        assert r1.record_hash == r2.record_hash

    def test_hash_changes_with_different_inputs(self):
        ts = _utc()
        base = dict(
            audit_id="aud_fixed",
            timestamp_utc=ts,
            subscription_id="sub_test123",
            actor="AGENT_POLICY_ENGINE",
            rule_triggered="TEST_RULE",
            previous_hash="genesis",
        )
        r1 = AuditRecord(**base, inputs={"k": "v1"})
        r2 = AuditRecord(**base, inputs={"k": "v2"})
        assert r1.record_hash != r2.record_hash

    def test_hash_chain(self):
        """Two records form a verifiable chain."""
        r1 = AuditRecord(
            subscription_id="sub_test123",
            actor="AGENT_POLICY_ENGINE",
            rule_triggered="RULE_1",
        )
        r2 = AuditRecord(
            subscription_id="sub_test123",
            actor="AGENT_POLICY_ENGINE",
            rule_triggered="RULE_2",
            previous_hash=r1.record_hash,
        )
        assert r2.previous_hash == r1.record_hash
        assert r2.record_hash != r1.record_hash
