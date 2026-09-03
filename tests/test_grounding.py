"""Tests for narrator grounding validation and normalization."""

import pytest

from rra.domain.enums import ActionType, ChannelType
from rra.narrator.grounding import normalize_amount_to_paise, validate_grounding
from rra.narrator.schemas import (
    NarratorRequest,
    NarratorResponse,
    PolicyConstraints,
    TransactionContext,
)


def _make_request(**overrides) -> NarratorRequest:
    ctx_defaults = dict(
        subscription_id="sub_test999",
        customer_name="Aarav Sharma",
        amount_due_inr=2499.0,
        amount_due_paise=249900,
        failure_reason="insufficient_funds",
        attempt_count=1,
        action_type=ActionType.SMS_NUDGE,
        payment_link="https://rzp.io/i/sub_test999",
    )
    ctx_defaults.update(overrides)
    return NarratorRequest(
        transaction_context=TransactionContext(**ctx_defaults),
        policy_constraints=PolicyConstraints(),
    )


class TestGroundingNormalization:
    """Normalization testing for currency amounts."""

    def test_normalize_rupee_formats(self):
        assert normalize_amount_to_paise("Payment of ₹2,499.00 is due") == [249900]
        assert normalize_amount_to_paise("Amount: Rs. 2499") == [249900]
        assert normalize_amount_to_paise("Due: INR 2,499.50") == [249950]
        assert normalize_amount_to_paise("Pay 500.00 now") == [50000]


class TestGroundingValidation:
    """Grounding assertion tests."""

    def test_valid_grounded_response_passes(self):
        req = _make_request()
        resp = NarratorResponse(
            message_body="Hi Aarav Sharma, your payment of ₹2,499.00 for subscription sub_test999 is pending. Link: https://rzp.io/i/sub_test999",
            channel=ChannelType.SMS,
        )
        violations = validate_grounding(req, resp)
        assert len(violations) == 0

    def test_fabricated_amount_caught(self):
        req = _make_request(amount_due_paise=249900, amount_due_inr=2499.0)
        resp = NarratorResponse(
            message_body="Hi Aarav Sharma, your payment of ₹5,000.00 for subscription sub_test999 is pending.",
            channel=ChannelType.SMS,
        )
        violations = validate_grounding(req, resp)
        assert len(violations) > 0
        assert violations[0].violation_type == "unauthorized_amount"

    def test_prohibited_action_discount_caught(self):
        req = _make_request()
        resp = NarratorResponse(
            message_body="Hi Aarav, pay now for subscription sub_test999 and get 10% discount on your bill.",
            channel=ChannelType.SMS,
        )
        violations = validate_grounding(req, resp)
        assert len(violations) > 0
        assert violations[0].violation_type == "prohibited_action"
