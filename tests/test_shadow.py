"""Tests for shadow-mode ingestion and runner."""

from datetime import datetime, timezone
import pytest

from rra.domain.enums import FailureCode
from rra.shadow.ingest import ingest_webhook_event
from rra.shadow.runner import ShadowRunner


def test_shadow_ingest_mapped_error():
    event = {
        "id": "evt_test_01",
        "entity": "event",
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_01",
                    "amount": 249900,
                    "currency": "INR",
                    "status": "failed",
                    "method": "upi",
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_source": "customer",
                    "error_step": "payment_authentication",
                    "error_reason": "insufficient_funds",
                    "created_at": 1775010000,
                }
            }
        },
    }
    res = ingest_webhook_event(event)
    assert res.is_mapped is True
    assert res.failure_code == FailureCode.INSUFFICIENT_FUNDS
    assert res.case is not None
    assert res.case.amount_due_paise == 249900


def test_shadow_ingest_unmapped_error():
    event = {
        "id": "evt_test_02",
        "entity": "event",
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_02",
                    "amount": 100000,
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_source": "customer",
                    "error_step": "risk_evaluation",
                    "error_reason": "unmapped_custom_fraud_flag",
                }
            }
        },
    }
    res = ingest_webhook_event(event)
    assert res.is_mapped is False
    assert res.failure_code is None
    assert res.unmapped_reason is not None


def test_shadow_runner_batch_evaluation():
    events = [
        {
            "id": "evt_01",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_01",
                        "amount": 120000,
                        "error_code": "BAD_REQUEST_ERROR",
                        "error_source": "customer",
                        "error_step": "mandate_cancellation",
                        "error_reason": "mandate_revoked",
                    }
                }
            },
        },
        {
            "id": "evt_02",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_02",
                        "amount": 250000,
                        "error_code": "BAD_REQUEST_ERROR",
                        "error_source": "customer",
                        "error_step": "payment_authentication",
                        "error_reason": "insufficient_funds",
                    }
                }
            },
        },
    ]

    runner = ShadowRunner(now=datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc))
    summary = runner.evaluate_batch(events)

    assert summary.total_events == 2
    assert summary.mapped_events == 2
    assert summary.taxonomy_coverage_pct == 100.0
    assert summary.declined_chases_count == 1  # Mandate revoked correctly declined
    assert summary.proposed_actions_count == 1
    assert summary.legal_compliance_rate_pct == 100.0
