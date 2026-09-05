"""Razorpay Webhook Handler & Signature Verification.

Verifies X-Razorpay-Signature HMAC-SHA256 digests over raw request bodies
and routes gateway events into the deterministic FSM engine and audit ledger.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timezone
from typing import Any

from rra.audit.ledger import Ledger
from rra.domain.enums import CaseStatus, FailureCode
from rra.domain.models import Case
from rra.engine.fsm import transition
from rra.engine.policy import next_action
from rra.engine.taxonomy import classify


class InvalidWebhookSignatureError(ValueError):
    """Raised when HMAC-SHA256 signature verification fails."""
    pass


class WebhookManager:
    """Webhook ingestion manager with idempotency and signature verification."""

    def __init__(self, secret: str | None = None, ledger: Ledger | None = None) -> None:
        self.secret = secret or os.getenv("WEBHOOK_SECRET", "mocksecret123")
        self.ledger = ledger or Ledger()
        self.processed_event_ids: set[str] = set()
        self.active_cases: dict[str, Case] = {}

    def verify_signature(self, raw_body: bytes, signature_header: str) -> bool:
        """Verify HMAC-SHA256 digest of raw request body against signature header.

        Uses hmac.compare_digest to prevent timing attacks.
        """
        if not signature_header:
            return False

        expected_digest = hmac.new(
            key=self.secret.encode("utf-8"),
            msg=raw_body,
            digestmod=hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_digest, signature_header)

    def process_event(
        self,
        raw_body: bytes,
        signature_header: str,
        event_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Process an inbound gateway webhook event.

        Args:
            raw_body: Exact bytes of HTTP request body.
            signature_header: Content of X-Razorpay-Signature header.
            event_payload: Parsed JSON payload.

        Returns:
            Dict summary of processing action taken.
        """
        if not self.verify_signature(raw_body, signature_header):
            raise InvalidWebhookSignatureError("HMAC-SHA256 signature verification failed.")

        event_id = str(event_payload.get("account_id", "")) + "_" + str(event_payload.get("created_at", ""))
        event_type = str(event_payload.get("event", ""))

        # Idempotency check
        if event_id in self.processed_event_ids:
            return {"status": "ignored", "reason": "duplicate_event_id"}

        self.processed_event_ids.add(event_id)

        payload_entity = event_payload.get("payload", {})
        sub_data = payload_entity.get("subscription", {}).get("entity", {})
        payment_data = payload_entity.get("payment", {}).get("entity", {})

        sub_id = sub_data.get("id") or payment_data.get("subscription_id") or "sub_unknown"

        # Dispatch event
        if event_type == "payment.failed":
            error_obj = payment_data.get("error", {})
            failure_code = classify(error_obj)

            # Look up or create case
            case = self.active_cases.get(sub_id)
            if not case:
                case = Case(
                    subscription_id=sub_id,
                    customer_name=payment_data.get("notes", {}).get("customer_name", "Customer"),
                    amount_due_paise=int(payment_data.get("amount", 249900)),
                    failure_code=failure_code,
                    phone_number=payment_data.get("contact"),
                )
                self.active_cases[sub_id] = case

            # Append audit log record for the raw ingestion event
            self.ledger.append(
                subscription_id=sub_id,
                actor="RAZORPAY_WEBHOOK_HANDLER",
                rule_triggered="EVENT_PAYMENT_FAILED",
                inputs={"raw_event": event_type, "error": error_obj},
                execution_payload={"failure_code": failure_code.value},
                compliance_check={"signature_verified": True},
            )

            # Run the deterministic policy engine on the freshly classified case and
            # record its decision — same engine.policy.next_action used by the
            # simulator and CLI demo, now wired into the live webhook path.
            next_act = next_action(
                case, [], datetime.now(timezone.utc), use_smart_scheduling=True, voice_enabled=True
            )
            if next_act is not None:
                self.ledger.append(
                    subscription_id=sub_id,
                    actor="AGENT_POLICY_ENGINE",
                    rule_triggered=next_act.rule_id or next_act.action_type.value.upper(),
                    inputs={"escalation_level": case.escalation_level.value, "failure_code": failure_code.value},
                    execution_payload={
                        "action_type": next_act.action_type.value,
                        "channel": next_act.channel.value if next_act.channel else None,
                        "scheduled_at": next_act.scheduled_at.isoformat(),
                    },
                    compliance_check={"legally_compliant": True},
                )
                action_summary: dict[str, Any] | None = {
                    "action_type": next_act.action_type.value,
                    "channel": next_act.channel.value if next_act.channel else None,
                    "scheduled_at": next_act.scheduled_at.isoformat(),
                }
            else:
                self.ledger.append(
                    subscription_id=sub_id,
                    actor="AGENT_POLICY_ENGINE",
                    rule_triggered="GUARD_DECLINED_CHASE" if case.status == CaseStatus.HALTED else "HALT_NO_FURTHER_ACTION",
                    inputs={"escalation_level": case.escalation_level.value, "failure_code": failure_code.value},
                    execution_payload={"case_status": case.status.value},
                    compliance_check={"legally_compliant": True},
                )
                action_summary = None

            return {
                "status": "processed",
                "event": event_type,
                "failure_code": failure_code.value,
                "case_id": case.case_id,
                "subscription_id": sub_id,
                "escalation_level": case.escalation_level.value,
                "case_status": case.status.value,
                "next_action": action_summary,
            }

        elif event_type == "subscription.charged":
            case = self.active_cases.get(sub_id)
            if case:
                transition(case, "PAYMENT_SUCCESS")

            self.ledger.append(
                subscription_id=sub_id,
                actor="RAZORPAY_WEBHOOK_HANDLER",
                rule_triggered="EVENT_SUBSCRIPTION_CHARGED",
                inputs={"raw_event": event_type},
                execution_payload={"status": "settled"},
                compliance_check={"signature_verified": True},
            )
            return {"status": "processed", "event": event_type, "case_status": "settled"}

        elif event_type == "subscription.halted":
            case = self.active_cases.get(sub_id)
            if case and case.status != CaseStatus.SETTLED:
                transition(case, "HARD_STOP")

            self.ledger.append(
                subscription_id=sub_id,
                actor="RAZORPAY_WEBHOOK_HANDLER",
                rule_triggered="EVENT_SUBSCRIPTION_HALTED",
                inputs={"raw_event": event_type},
                execution_payload={"status": "halted"},
                compliance_check={"signature_verified": True},
            )
            return {"status": "processed", "event": event_type, "case_status": "halted"}

        return {"status": "ignored", "reason": f"unhandled_event_type_{event_type}"}
