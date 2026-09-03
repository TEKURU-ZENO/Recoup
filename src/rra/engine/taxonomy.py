"""Deterministic error classification taxonomy.

Maps payment gateway (Razorpay) error objects to FailureCode.
Unknown error combinations explicitly raise an exception rather than
silently defaulting — misclassification can cause invalid recovery actions.
"""

from __future__ import annotations

from typing import Any

from rra.domain.enums import FailureCode


def classify(error_object: dict[str, Any]) -> FailureCode:
    """Classify a raw gateway error object into a FailureCode.

    Args:
        error_object: Dict containing error details (source, step, reason, code, description).

    Returns:
        The matched FailureCode enum.

    Raises:
        ValueError: If the error combination cannot be classified deterministically.
    """
    reason = str(error_object.get("reason", "")).lower()
    source = str(error_object.get("source", "")).lower()
    step = str(error_object.get("step", "")).lower()
    code = str(error_object.get("code", "")).lower()

    # 1. Direct reason matching
    if reason in ("insufficient_funds", "insufficient_balance", "low_balance"):
        return FailureCode.INSUFFICIENT_FUNDS

    if reason in ("bank_downtime", "gateway_error", "issuer_down", "bank_offline"):
        return FailureCode.BANK_DOWNTIME

    if reason in ("card_expired", "expired_card", "card_expiry"):
        return FailureCode.CARD_EXPIRED

    if reason in ("3ds_dropoff", "authentication_failed", "customer_abandoned_3ds", "otp_timeout"):
        return FailureCode.THREE_DS_DROPOFF

    if reason in ("mandate_revoked", "customer_cancelled", "mandate_cancelled", "consent_revoked"):
        return FailureCode.MANDATE_REVOKED

    if reason in ("payment_timed_out", "gateway_timeout", "request_timeout", "network_timeout"):
        return FailureCode.PAYMENT_TIMED_OUT

    if reason in ("input_validation_failed", "invalid_account", "invalid_vpa", "bad_request"):
        return FailureCode.INPUT_VALIDATION_FAILED

    # 2. Step and Code fallback diagnostics
    if code in ("server_error", "500", "502", "503", "gateway_error"):
        return FailureCode.BANK_DOWNTIME

    if step == "payment_authentication" and "insufficient" in reason:
        return FailureCode.INSUFFICIENT_FUNDS

    if step == "payment_authentication" and ("timeout" in reason or "timed_out" in reason):
        return FailureCode.PAYMENT_TIMED_OUT

    if step == "payment_authorization" and ("cancelled" in reason or "revoked" in reason):
        return FailureCode.MANDATE_REVOKED

    # Unknown combination — raise explicitly!
    raise ValueError(
        f"Unknown error classification payload: code='{code}', source='{source}', step='{step}', reason='{reason}'"
    )
