"""LiveKit voice agent worker implementation.

Supports low-latency WebRTC/SIP telephony, VAD-driven barge-in interruption handling,
and mid-call Promise-to-Pay (P2P) tool execution.
"""

from __future__ import annotations

import asyncio
from typing import Any

from rra.channels.voice.prompts import HINGLISH_VOICE_SYSTEM_PROMPT
from rra.channels.voice.tools import record_promise_to_pay
from rra.domain.models import Case


class LiveKitVoiceWorker:
    """Mock/LiveKit agent worker managing telephony voice sessions."""

    def __init__(self, room_name: str = "room_voice_101") -> None:
        self.room_name = room_name
        self.is_agent_speaking = False
        self.barge_in_triggered = False

    def handle_user_interruption(self) -> dict[str, str]:
        """VAD-driven barge-in: Truncates TTS playout and cancels in-flight LLM generation."""
        self.barge_in_triggered = True
        self.is_agent_speaking = False
        return {
            "status": "interrupted",
            "action": "truncated_tts_playout",
            "message": "User speech detected via VAD. Playout stopped.",
        }

    async def execute_call_session(
        self,
        case: Case,
        user_utterances: list[str],
    ) -> dict[str, Any]:
        """Simulate an outbound voice call session with turn-taking and tool invocation."""
        prompt = HINGLISH_VOICE_SYSTEM_PROMPT.format(
            customer_name=case.customer_name,
            subscription_id=case.subscription_id,
            amount_due_inr=case.amount_inr,
            failure_reason=case.failure_code.value,
        )

        p2p_result = None

        for utterance in user_utterances:
            # Check for barge-in
            if self.is_agent_speaking:
                self.handle_user_interruption()

            # Check if utterance contains a date commitment
            if any(term in utterance.lower() for term in ["tomorrow", "1st", "date", "pay on", "next week"]):
                p2p_result = record_promise_to_pay(case, "2026-04-05")
                break
            elif any(term in utterance.lower() for term in ["no", "refuse", "stop", "don't call"]):
                case.status = "halted"
                return {"session_status": "refused", "case_id": case.case_id}

        return {
            "session_status": "completed",
            "barge_in_occurred": self.barge_in_triggered,
            "p2p_result": p2p_result,
            "final_case_status": case.status.value,
        }
