"""Tests for webhook ingestion, HMAC-SHA256 verification, and FSM event routing."""

import hashlib
import hmac
import json
import time

import pytest

from rra.domain.enums import FailureCode
from rra.gateway.webhooks import InvalidWebhookSignatureError, WebhookManager


def _make_webhook_payload(event="payment.failed", sub_id="sub_test123", reason="insufficient_funds") -> tuple[bytes, str, dict]:
    payload = {
        "entity": "event",
        "account_id": "acc_test123",
        "event": event,
        "created_at": 1700000000,
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test999",
                    "amount": 249900,
                    "subscription_id": sub_id,
                    "contact": "+919876543210",
                    "error": {
                        "code": "BAD_REQUEST_ERROR",
                        "source": "customer",
                        "step": "payment_authentication",
                        "reason": reason,
                    },
                    "notes": {"customer_name": "Aarav Sharma"},
                }
            }
        },
    }
    raw_body = json.dumps(payload).encode("utf-8")
    secret = "mocksecret123"
    signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return raw_body, signature, payload


class TestWebhooks:
    """Webhook verification and event routing tests."""

    def test_valid_signature_verification(self):
        wm = WebhookManager(secret="mocksecret123")
        raw_body, sig, _ = _make_webhook_payload()
        assert wm.verify_signature(raw_body, sig) is True

    def test_tampered_signature_rejected(self):
        wm = WebhookManager(secret="mocksecret123")
        raw_body, _, payload = _make_webhook_payload()
        invalid_sig = "0" * 64
        with pytest.raises(InvalidWebhookSignatureError, match="signature verification failed"):
            wm.process_event(raw_body, invalid_sig, payload)

    def test_idempotency_duplicate_event(self):
        wm = WebhookManager(secret="mocksecret123")
        raw_body, sig, payload = _make_webhook_payload()
        r1 = wm.process_event(raw_body, sig, payload)
        assert r1["status"] == "processed"

        r2 = wm.process_event(raw_body, sig, payload)
        assert r2["status"] == "ignored"
        assert r2["reason"] == "duplicate_event_id"

    def test_end_to_end_payment_failed_event(self):
        wm = WebhookManager(secret="mocksecret123")
        raw_body, sig, payload = _make_webhook_payload(sub_id="sub_e2e_1", reason="card_expired")
        result = wm.process_event(raw_body, sig, payload)

        assert result["status"] == "processed"
        assert result["failure_code"] == FailureCode.CARD_EXPIRED

        # Verify case created
        case = wm.active_cases.get("sub_e2e_1")
        assert case is not None
        assert case.failure_code == FailureCode.CARD_EXPIRED

        # Verify audit ledger recorded entries: raw ingestion + policy decision
        audit_records = wm.ledger.for_subscription("sub_e2e_1")
        assert len(audit_records) == 2
        assert audit_records[0].rule_triggered == "EVENT_PAYMENT_FAILED"
        assert audit_records[1].actor == "AGENT_POLICY_ENGINE"

        # card_expired routes to Digital_Nudge and dispatches a method-switch link,
        # never a futile backend retry.
        assert result["escalation_level"] == "digital_nudge"
        assert result["next_action"]["action_type"] == "method_switch_link"

    def test_mandate_revoked_is_refused_not_chased(self):
        wm = WebhookManager(secret="mocksecret123")
        raw_body, sig, payload = _make_webhook_payload(sub_id="sub_e2e_2", reason="mandate_revoked")
        result = wm.process_event(raw_body, sig, payload)

        assert result["status"] == "processed"
        assert result["case_status"] == "halted"
        assert result["next_action"] is None

        audit_records = wm.ledger.for_subscription("sub_e2e_2")
        assert len(audit_records) == 2
        assert audit_records[1].rule_triggered == "GUARD_DECLINED_CHASE"
