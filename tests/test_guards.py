"""Tests for engine guardrails."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from rra.domain.enums import ActionType, ChannelType, FailureCode
from rra.domain.models import Action, Case, Outcome
from rra.engine.guards import evaluate

IST = ZoneInfo("Asia/Kolkata")


def _utc_ist(year=2026, month=4, day=1, hour_ist=10, minute_ist=0) -> datetime:
    """Create a UTC datetime corresponding to a specific IST time."""
    dt_ist = datetime(year, month, day, hour_ist, minute_ist, tzinfo=IST)
    return dt_ist.astimezone(timezone.utc)


def _make_case(**overrides) -> Case:
    defaults = dict(
        case_id="case_guard_test",
        subscription_id="sub_123",
        customer_name="Aarav",
        amount_due_paise=249900,
        failure_code=FailureCode.INSUFFICIENT_FUNDS,
        phone_number="+919876543210",
        is_dnd=False,
        is_opted_out=False,
        created_at=_utc_ist(hour_ist=10),
        updated_at=_utc_ist(hour_ist=10),
    )
    defaults.update(overrides)
    return Case(**defaults)


class TestGuards:
    """Individual guardrail tests."""

    def test_opt_out_hard_stop(self):
        case = _make_case(is_opted_out=True)
        act = Action(case_id=case.case_id, action_type=ActionType.SMS_NUDGE, scheduled_at=_utc_ist(hour_ist=10))
        dec = evaluate(case, act, [], _utc_ist(hour_ist=10))
        assert not dec.allowed
        assert dec.rule_id == "OPT_OUT"

    def test_revocation_hard_stop(self):
        case = _make_case(failure_code=FailureCode.MANDATE_REVOKED)
        act = Action(case_id=case.case_id, action_type=ActionType.BACKEND_RETRY, scheduled_at=_utc_ist(hour_ist=10))
        dec = evaluate(case, act, [], _utc_ist(hour_ist=10))
        assert not dec.allowed
        assert dec.rule_id == "REVOCATION"

    def test_max_retries_limit(self):
        case = _make_case()
        t = _utc_ist(hour_ist=10)
        # Create 3 past backend retries
        history = []
        for i in range(3):
            a = Action(case_id=case.case_id, action_type=ActionType.BACKEND_RETRY, scheduled_at=t, executed_at=t)
            o = Outcome(case_id=case.case_id, action_id=a.action_id, success=False, amount_recovered_paise=0, timestamp=t)
            history.append((a, o))

        # 4th retry proposed
        act = Action(case_id=case.case_id, action_type=ActionType.BACKEND_RETRY, scheduled_at=t)
        dec = evaluate(case, act, history, t)
        assert not dec.allowed
        assert dec.rule_id == "MAX_RETRIES"

    def test_dnd_scrub_blocks_nudge(self):
        case = _make_case(is_dnd=True)
        t = _utc_ist(hour_ist=10)
        act = Action(case_id=case.case_id, action_type=ActionType.SMS_NUDGE, channel=ChannelType.SMS, scheduled_at=t)
        dec = evaluate(case, act, [], t)
        assert not dec.allowed
        assert dec.rule_id == "DND_SCRUB"

    def test_dnd_scrub_allows_backend_retry(self):
        """DND customers still allow silent background API retries."""
        case = _make_case(is_dnd=True)
        t = _utc_ist(hour_ist=10)
        act = Action(case_id=case.case_id, action_type=ActionType.BACKEND_RETRY, scheduled_at=t)
        dec = evaluate(case, act, [], t)
        assert dec.allowed

    def test_trai_hours_18_59_ist_allowed(self):
        """Action at 18:59 IST is inside allowed TRAI window (09:00-19:00 IST)."""
        case = _make_case()
        t = _utc_ist(day=1, hour_ist=18, minute_ist=59)
        act = Action(case_id=case.case_id, action_type=ActionType.SMS_NUDGE, channel=ChannelType.SMS, scheduled_at=t)
        dec = evaluate(case, act, [], t)
        assert dec.allowed

    def test_trai_hours_19_01_ist_deferred(self):
        """Action at 19:01 IST is deferred to 09:30 IST next morning."""
        case = _make_case()
        t = _utc_ist(day=1, hour_ist=19, minute_ist=1)
        act = Action(case_id=case.case_id, action_type=ActionType.SMS_NUDGE, channel=ChannelType.SMS, scheduled_at=t)
        dec = evaluate(case, act, [], t)
        assert not dec.allowed
        assert dec.rule_id == "TRAI_HOURS"
        assert dec.deferred_until is not None
        
        # Check deferred time is 09:30 IST next morning (April 2 09:30 IST)
        deferred_ist = dec.deferred_until.astimezone(IST)
        assert deferred_ist.day == 2
        assert deferred_ist.hour == 9
        assert deferred_ist.minute == 30

    def test_cooling_off_blocks_contact_under_48h(self):
        """Customer contact attempted within 48h of prior contact must be deferred."""
        case = _make_case()
        t1 = _utc_ist(day=1, hour_ist=10)
        a_sms = Action(case_id=case.case_id, action_type=ActionType.SMS_NUDGE, channel=ChannelType.SMS, scheduled_at=t1, executed_at=t1)
        o_sms = Outcome(case_id=case.case_id, action_id=a_sms.action_id, success=False, amount_recovered_paise=0, timestamp=t1)
        history = [(a_sms, o_sms)]

        # Contact attempted at Day 2 10:00 IST (only 24h later) -> MUST BE BLOCKED
        t2 = _utc_ist(day=2, hour_ist=10)
        act_nudge = Action(case_id=case.case_id, action_type=ActionType.WHATSAPP_NUDGE, channel=ChannelType.WHATSAPP, scheduled_at=t2)
        dec = evaluate(case, act_nudge, history, t2)
        assert not dec.allowed
        assert dec.rule_id == "COOLING_OFF"
        assert dec.deferred_until is not None

    def test_cooling_off_not_reset_by_backend_retry(self):
        """Critical invariant: silent backend retries DO NOT reset the 48h cooling-off clock."""
        case = _make_case()
        t1 = _utc_ist(day=1, hour_ist=10)
        
        # Customer contact (SMS) executed at Day 1 10:00 IST
        a_sms = Action(case_id=case.case_id, action_type=ActionType.SMS_NUDGE, channel=ChannelType.SMS, scheduled_at=t1, executed_at=t1)
        o_sms = Outcome(case_id=case.case_id, action_id=a_sms.action_id, success=False, amount_recovered_paise=0, timestamp=t1)
        
        # Silent backend retry executed at Day 2 10:00 IST (24h later)
        t2 = _utc_ist(day=2, hour_ist=10)
        a_retry = Action(case_id=case.case_id, action_type=ActionType.BACKEND_RETRY, scheduled_at=t2, executed_at=t2)
        o_retry = Outcome(case_id=case.case_id, action_id=a_retry.action_id, success=False, amount_recovered_paise=0, timestamp=t2)

        history = [(a_sms, o_sms), (a_retry, o_retry)]

        # At Day 2 15:00 IST (29h after SMS), contact is still blocked by SMS cooling-off
        t_blocked = _utc_ist(day=2, hour_ist=15)
        act_blocked = Action(case_id=case.case_id, action_type=ActionType.WHATSAPP_NUDGE, channel=ChannelType.WHATSAPP, scheduled_at=t_blocked)
        dec_blocked = evaluate(case, act_blocked, history, t_blocked)
        assert not dec_blocked.allowed
        assert dec_blocked.rule_id == "COOLING_OFF"

        # At Day 3 10:30 IST (48.5h after Day 1 10:00 IST SMS), contact is ALLOWED
        # even though backend retry was at Day 2 10:00 IST (only 24.5h ago)
        t3 = _utc_ist(day=3, hour_ist=10, minute_ist=30)
        act_nudge = Action(case_id=case.case_id, action_type=ActionType.WHATSAPP_NUDGE, channel=ChannelType.WHATSAPP, scheduled_at=t3)

        dec = evaluate(case, act_nudge, history, t3)
        assert dec.allowed, f"Cooling off incorrectly triggered by backend retry! Reason: {dec.reason}"
