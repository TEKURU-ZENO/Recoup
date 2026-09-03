"""Shadow-mode ingestion and taxonomy mapping for real merchant webhook payloads.

Validates:
1. Taxonomy coverage % against live Razorpay error payloads.
2. Identifies unmapped error codes for diagnostic refinement.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from rra.domain.enums import CaseStatus, FailureCode, InstrumentType
from rra.domain.models import Case
from rra.engine.taxonomy import classify


@dataclass
class ShadowIngestResult:
    """Result of ingesting and classifying a raw merchant webhook event."""

    event_id: str
    payment_id: str
    amount_paise: int
    raw_error: dict[str, Any]
    is_mapped: bool
    failure_code: FailureCode | None
    unmapped_reason: str | None
    case: Case | None


def ingest_webhook_event(raw_event: dict[str, Any]) -> ShadowIngestResult:
    """Parse and classify a raw Razorpay payment.failed webhook event."""
    event_id = raw_event.get("id", f"evt_{hash(str(raw_event)) & 0xFFFFFFFF:08x}")
    payload = raw_event.get("payload", {}).get("payment", {}).get("entity", {})
    if not payload:
        payload = raw_event  # Direct payment entity format

    payment_id = payload.get("id", "pay_unknown")
    amount_paise = int(payload.get("amount", 0))
    error_obj = payload.get("error", {})
    if not error_obj and "error_code" in payload:
        error_obj = {
            "code": payload.get("error_code"),
            "description": payload.get("error_description"),
            "source": payload.get("error_source", "gateway"),
            "step": payload.get("error_step", "payment_authorization"),
            "reason": payload.get("error_reason"),
        }

    try:
        fc = classify(error_obj)
        is_mapped = True
        unmapped_reason = None
    except ValueError as e:
        fc = None
        is_mapped = False
        unmapped_reason = str(e)

    case = None
    if is_mapped and fc is not None:
        # Determine instrument type
        method = payload.get("method", "upi")
        if method == "upi":
            inst = InstrumentType.UPI_AUTOPAY
        elif method == "card":
            inst = InstrumentType.CARD_RECURRING
        else:
            inst = InstrumentType.EMANDATE

        created_at_ts = payload.get("created_at")
        if isinstance(created_at_ts, (int, float)):
            created_at = datetime.fromtimestamp(created_at_ts, tz=timezone.utc)
        else:
            created_at = datetime.now(timezone.utc)

        case = Case(
            case_id=f"case_shadow_{payment_id}",
            subscription_id=payload.get("subscription_id", f"sub_{payment_id[:10]}"),
            customer_name=payload.get("notes", {}).get("customer_name", "Valued Customer"),
            amount_due_paise=amount_paise,
            failure_code=fc,
            instrument_type=inst,
            phone_number=payload.get("contact", "+919876543210"),
            created_at=created_at,
            updated_at=created_at,
        )

    return ShadowIngestResult(
        event_id=event_id,
        payment_id=payment_id,
        amount_paise=amount_paise,
        raw_error=error_obj,
        is_mapped=is_mapped,
        failure_code=fc,
        unmapped_reason=unmapped_reason,
        case=case,
    )
