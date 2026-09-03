"""Tests for the synthetic portfolio generator."""

from datetime import datetime, timezone

import pytest

from rra.domain.enums import FailureCode
from rra.sim.portfolio import generate_portfolio


def _utc(year=2026, month=4, day=1, hour=0):
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


class TestPortfolioBasics:
    """Basic portfolio generation tests."""

    def test_batch_size(self):
        batch = generate_portfolio(seed=42, n=215)
        assert len(batch) == 215

    def test_custom_batch_size(self):
        batch = generate_portfolio(seed=42, n=50)
        assert len(batch) == 50

    def test_all_cases_active(self):
        batch = generate_portfolio(seed=42, n=100)
        for case in batch:
            assert case.status == "active"

    def test_all_cases_ingested(self):
        batch = generate_portfolio(seed=42, n=100)
        for case in batch:
            assert case.escalation_level == "ingested"


class TestAmountDistribution:
    """Verify amount distribution is log-normal and in expected range."""

    def test_amounts_positive(self):
        batch = generate_portfolio(seed=42, n=200)
        for case in batch:
            assert case.amount_due_paise > 0

    def test_amounts_in_range(self):
        """All amounts within floor (₹300) and cap (₹50,000)."""
        batch = generate_portfolio(seed=42, n=500)
        for case in batch:
            assert case.amount_due_paise >= 30000, f"Below floor: {case.amount_due_paise}"
            assert case.amount_due_paise <= 5000000, f"Above cap: {case.amount_due_paise}"

    def test_median_roughly_correct(self):
        """Median should be roughly ~₹1,200."""
        batch = generate_portfolio(seed=42, n=1000)
        amounts = sorted(c.amount_due_paise for c in batch)
        median = amounts[len(amounts) // 2]
        median_inr = median / 100
        # Allow wide range: 500-3000
        assert 500 < median_inr < 3000, f"Median: ₹{median_inr}"

    def test_has_high_value_cases(self):
        """There should be cases above ₹5,000 (the L3 voice gate)."""
        batch = generate_portfolio(seed=42, n=215)
        high_value = [c for c in batch if c.amount_due_paise >= 500000]
        assert len(high_value) > 0, "No high-value cases above ₹5,000"

    def test_not_all_same_amount(self):
        batch = generate_portfolio(seed=42, n=100)
        amounts = {c.amount_due_paise for c in batch}
        assert len(amounts) > 10


class TestFailureCodeDistribution:
    """Verify failure codes follow the target distribution."""

    def test_all_failure_codes_present(self):
        batch = generate_portfolio(seed=42, n=500)
        codes = {c.failure_code for c in batch}
        expected = {
            FailureCode.INSUFFICIENT_FUNDS,
            FailureCode.BANK_DOWNTIME,
            FailureCode.CARD_EXPIRED,
            FailureCode.THREE_DS_DROPOFF,
            FailureCode.MANDATE_REVOKED,
            FailureCode.PAYMENT_TIMED_OUT,
        }
        assert expected.issubset(codes)

    def test_insufficient_funds_is_largest(self):
        """insufficient_funds should be the most common (target: 42%)."""
        batch = generate_portfolio(seed=42, n=1000)
        counts = {}
        for case in batch:
            counts[case.failure_code] = counts.get(case.failure_code, 0) + 1
        assert counts.get(FailureCode.INSUFFICIENT_FUNDS, 0) > counts.get(
            FailureCode.BANK_DOWNTIME, 0
        )

    def test_approximate_distribution(self):
        """Failure code percentages should be roughly correct."""
        batch = generate_portfolio(seed=42, n=2000)
        total = len(batch)
        counts = {}
        for case in batch:
            counts[case.failure_code] = counts.get(case.failure_code, 0) + 1

        insuf_pct = counts.get(FailureCode.INSUFFICIENT_FUNDS, 0) / total
        # Target is 42%, allow 30-55% for seeded variance
        assert 0.30 < insuf_pct < 0.55, f"insufficient_funds: {insuf_pct:.1%}"


class TestCustomerMetadata:
    """Verify customer metadata generation."""

    def test_case_ids_unique(self):
        batch = generate_portfolio(seed=42, n=215)
        ids = [c.case_id for c in batch]
        assert len(ids) == len(set(ids))

    def test_subscription_ids_unique(self):
        batch = generate_portfolio(seed=42, n=215)
        ids = [c.subscription_id for c in batch]
        assert len(ids) == len(set(ids))

    def test_has_dnd_customers(self):
        batch = generate_portfolio(seed=42, n=200)
        dnd_count = sum(1 for c in batch if c.is_dnd)
        assert dnd_count > 0, "No DND customers generated"

    def test_has_customers_without_phone(self):
        batch = generate_portfolio(seed=42, n=500)
        no_phone = sum(1 for c in batch if c.phone_number is None)
        assert no_phone > 0, "All customers have phones"

    def test_phone_numbers_format(self):
        batch = generate_portfolio(seed=42, n=100)
        for case in batch:
            if case.phone_number:
                assert case.phone_number.startswith("+91")

    def test_timestamps_are_utc(self):
        batch = generate_portfolio(seed=42, n=100)
        for case in batch:
            assert case.created_at.tzinfo is not None

    def test_naive_base_time_rejected(self):
        with pytest.raises(ValueError):
            generate_portfolio(seed=42, base_time=datetime(2026, 4, 1))
