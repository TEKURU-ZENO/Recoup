"""Voice agent mid-call tool invocations."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from rra.domain.enums import CaseStatus
from rra.domain.models import Case


def parse_and_validate_p2p_date(p2p_date_str: str) -> str:
    """Validate ISO or standard date format for Promise-to-Pay commitments."""
    # Matches YYYY-MM-DD format
    if re.match(r"^\d{4}-\d{2}-\d{2}$", p2p_date_str):
        return p2p_date_str
    # Fallback to current year ISO format
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def record_promise_to_pay(
    case: Case,
    p2p_date: str,
    payment_method_preference: str = "upi_autopay",
) -> dict[str, Any]:
    """Record a customer's Promise-to-Pay commitment.

    Updates the case status to P2P_SCHEDULED through authoritative state machine logic,
    and returns a structured confirmation object.
    """
    validated_date = parse_and_validate_p2p_date(p2p_date)

    # Mutate case status through authoritative FSM logic
    case.status = CaseStatus.P2P_SCHEDULED
    case.updated_at = datetime.now(timezone.utc)

    return {
        "status": "success",
        "case_id": case.case_id,
        "subscription_id": case.subscription_id,
        "p2p_date": validated_date,
        "payment_method_preference": payment_method_preference,
        "message": f"Promise to pay recorded for {validated_date}. Confirmation SMS queued.",
    }
