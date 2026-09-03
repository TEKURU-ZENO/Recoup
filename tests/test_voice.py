"""Tests for voice channel worker, barge-in handling, and P2P tool execution."""

import asyncio
from datetime import datetime, timezone

import pytest

from rra.channels.voice.tools import parse_and_validate_p2p_date, record_promise_to_pay
from rra.channels.voice.worker import LiveKitVoiceWorker
from rra.domain.enums import CaseStatus, FailureCode
from rra.domain.models import Case


def _make_case() -> Case:
    return Case(
        case_id="case_voice_101",
        subscription_id="sub_voice123",
        customer_name="Priya Nair",
        amount_due_paise=650000,  # ₹6,500.00
        failure_code=FailureCode.INSUFFICIENT_FUNDS,
        phone_number="+919876543210",
        created_at=datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc),
    )


class TestVoiceArm:
    """Voice arm telephony and tool execution tests."""

    def test_p2p_date_validation(self):
        assert parse_and_validate_p2p_date("2026-04-05") == "2026-04-05"

    def test_record_promise_to_pay_mutates_status(self):
        case = _make_case()
        res = record_promise_to_pay(case, "2026-04-05")

        assert res["status"] == "success"
        assert res["p2p_date"] == "2026-04-05"
        assert case.status == CaseStatus.P2P_SCHEDULED

    def test_barge_in_interruption_handling(self):
        worker = LiveKitVoiceWorker()
        worker.is_agent_speaking = True

        result = worker.handle_user_interruption()
        assert result["status"] == "interrupted"
        assert worker.barge_in_triggered is True
        assert worker.is_agent_speaking is False

    @pytest.mark.asyncio
    async def test_voice_session_captures_p2p(self):
        worker = LiveKitVoiceWorker()
        case = _make_case()

        utterances = ["Hello?", "Yes, I will pay on next week 5th April."]
        session_res = await worker.execute_call_session(case, utterances)

        assert session_res["session_status"] == "completed"
        assert case.status == CaseStatus.P2P_SCHEDULED

    @pytest.mark.asyncio
    async def test_voice_session_refusal_halts_case(self):
        worker = LiveKitVoiceWorker()
        case = _make_case()

        utterances = ["I refuse to pay, please stop calling."]
        session_res = await worker.execute_call_session(case, utterances)

        assert session_res["session_status"] == "refused"
        assert case.status in ("halted", CaseStatus.HALTED)
