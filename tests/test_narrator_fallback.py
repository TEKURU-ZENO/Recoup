"""Tests for narrator client and template fallback behavior."""

from rra.domain.enums import ActionType
from rra.narrator.client import FencedNarratorClient
from rra.narrator.grounding import validate_grounding
from rra.narrator.schemas import (
    NarratorRequest,
    PolicyConstraints,
    TransactionContext,
)


def _make_request(action_type=ActionType.SMS_NUDGE) -> NarratorRequest:
    return NarratorRequest(
        transaction_context=TransactionContext(
            subscription_id="sub_fallback123",
            customer_name="Rohan Verma",
            amount_due_inr=1200.0,
            amount_due_paise=120000,
            failure_reason="card_expired",
            attempt_count=1,
            action_type=action_type,
            payment_link="https://rzp.io/i/sub_fallback123",
        ),
        policy_constraints=PolicyConstraints(),
    )


class TestNarratorFallback:
    """Template fallback verification."""

    def test_fallback_generates_grounded_message(self):
        client = FencedNarratorClient()
        req = _make_request()
        resp = client.generate_message(req)

        assert resp.grounding_passed is True
        assert "Rohan Verma" in resp.message_body
        assert "₹1,200.00" in resp.message_body
        assert "sub_fallback123" in resp.message_body

        # Confirm zero grounding violations on fallback output
        violations = validate_grounding(req, resp)
        assert len(violations) == 0

    def test_method_switch_fallback_content(self):
        client = FencedNarratorClient()
        req = _make_request(action_type=ActionType.METHOD_SWITCH_LINK)
        resp = client.generate_message(req)

        assert "expired" in resp.message_body
        assert "update your payment method" in resp.message_body
