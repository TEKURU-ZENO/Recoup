"""Tests for gateway error taxonomy classification."""

import pytest

from rra.domain.enums import FailureCode
from rra.engine.taxonomy import classify


class TestTaxonomy:
    """Error object taxonomy classification tests."""

    def test_insufficient_funds_reasons(self):
        for reason in ["insufficient_funds", "insufficient_balance", "low_balance"]:
            res = classify({"reason": reason})
            assert res == FailureCode.INSUFFICIENT_FUNDS

    def test_bank_downtime_reasons(self):
        for reason in ["bank_downtime", "gateway_error", "issuer_down", "bank_offline"]:
            res = classify({"reason": reason})
            assert res == FailureCode.BANK_DOWNTIME

    def test_card_expired_reasons(self):
        for reason in ["card_expired", "expired_card", "card_expiry"]:
            res = classify({"reason": reason})
            assert res == FailureCode.CARD_EXPIRED

    def test_3ds_dropoff_reasons(self):
        for reason in ["3ds_dropoff", "authentication_failed", "customer_abandoned_3ds", "otp_timeout"]:
            res = classify({"reason": reason})
            assert res == FailureCode.THREE_DS_DROPOFF

    def test_mandate_revoked_reasons(self):
        for reason in ["mandate_revoked", "customer_cancelled", "mandate_cancelled", "consent_revoked"]:
            res = classify({"reason": reason})
            assert res == FailureCode.MANDATE_REVOKED

    def test_payment_timed_out_reasons(self):
        for reason in ["payment_timed_out", "gateway_timeout", "request_timeout", "network_timeout"]:
            res = classify({"reason": reason})
            assert res == FailureCode.PAYMENT_TIMED_OUT

    def test_input_validation_failed_reasons(self):
        for reason in ["input_validation_failed", "invalid_account", "invalid_vpa", "bad_request"]:
            res = classify({"reason": reason})
            assert res == FailureCode.INPUT_VALIDATION_FAILED

    def test_fallback_code_500(self):
        res = classify({"code": "500", "reason": "something_unknown"})
        assert res == FailureCode.BANK_DOWNTIME

    def test_unknown_error_raises_exception(self):
        """Unknown combinations must raise ValueError, never silently default."""
        with pytest.raises(ValueError, match="Unknown error classification payload"):
            classify({
                "code": "FOOBAR_ERR",
                "source": "alien",
                "step": "quantum_teleport",
                "reason": "solar_flare",
            })
