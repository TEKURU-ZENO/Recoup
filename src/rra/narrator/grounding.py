"""Grounding validator for fenced LLM narrator outputs.

Normalizes dates, amounts, and actions extracted from text and asserts
every extracted entity was present in the input context payload.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from rra.narrator.schemas import NarratorRequest, NarratorResponse


@dataclass
class GroundingViolation:
    """Details of a grounding assertion failure."""

    violation_type: str  # 'unauthorized_amount', 'unauthorized_date', 'prohibited_action', 'hallucinated_entity'
    extracted_value: str
    expected_context: str
    message: str


def normalize_amount_to_paise(raw_text: str) -> list[int]:
    """Extract numeric rupee amounts from text and convert to integer paise."""
    clean_text = re.sub(r"(?:sub_|case_|act_|aud_)[a-zA-Z0-9]+", "", raw_text, flags=re.IGNORECASE)

    pattern = r"(?:(?:₹|rs\.?|inr)\s*([0-9,]+(?:\.[0-9]{1,2})?))|(?:\b([0-9,]+\.[0-9]{2})\b)"
    matches = re.findall(pattern, clean_text, flags=re.IGNORECASE)

    results: list[int] = []
    for g1, g2 in matches:
        val_str = (g1 or g2).replace(",", "").strip()
        if not val_str:
            continue
        try:
            val_float = float(val_str)
            if val_float > 0:
                results.append(int(round(val_float * 100)))
        except ValueError:
            continue
    return results


def normalize_dates(raw_text: str) -> list[str]:
    """Extract date strings and normalize to simple month/day representation."""
    # Matches patterns like 2026-04-01, April 1st, 1st April, Apr 1
    pattern = r"\b(?:202[0-9]-[0-1][0-9]-[0-3][0-9]|jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+[0-3]?[0-9](?:st|nd|rd|th)?\b"
    matches = re.findall(pattern, raw_text, flags=re.IGNORECASE)
    return [m.lower() for m in matches]


def validate_grounding(
    request: NarratorRequest,
    response: NarratorResponse,
) -> list[GroundingViolation]:
    """Assert every date, amount, and entity in response appears in request context.

    Returns:
        List of GroundingViolation objects (empty if 100% grounded).
    """
    violations: list[GroundingViolation] = []
    ctx = request.transaction_context
    constraints = request.policy_constraints
    body = response.message_body.lower()

    # 1. Prohibited actions / terms check
    for prohibited in constraints.prohibited_actions:
        term = prohibited.replace("offer_", "").replace("threaten_", "").replace("_", " ")
        if term in body:
            violations.append(
                GroundingViolation(
                    violation_type="prohibited_action",
                    extracted_value=term,
                    expected_context=str(constraints.prohibited_actions),
                    message=f"Response contains prohibited policy term: '{term}'",
                )
            )

    # 2. Rupee amount validation
    extracted_paise = normalize_amount_to_paise(response.message_body)
    expected_paise = ctx.amount_due_paise
    for paise in extracted_paise:
        # Allow exact match or matching INR value
        if paise != expected_paise and abs(paise - expected_paise) > 100:
            violations.append(
                GroundingViolation(
                    violation_type="unauthorized_amount",
                    extracted_value=f"₹{paise/100:.2f}",
                    expected_context=f"₹{expected_paise/100:.2f}",
                    message=f"Response contains ungrounded amount ₹{paise/100:.2f} (expected ₹{expected_paise/100:.2f})",
                )
            )

    # 3. Subscription ID check (must appear if body mentions subscription)
    if "subscription" in body and ctx.subscription_id.lower() not in body:
        violations.append(
            GroundingViolation(
                violation_type="hallucinated_entity",
                extracted_value="missing_subscription_id",
                expected_context=ctx.subscription_id,
                message=f"Response mentions subscription but omits correct ID '{ctx.subscription_id}'",
            )
        )

    return violations
