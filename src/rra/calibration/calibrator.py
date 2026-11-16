"""Empirical calibrator for Razorpay merchant failure cohorts.

Extracts maximum likelihood estimates (MLE) and Wilson score 95% confidence intervals
for recovery conversion rates across failure codes and channels.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from rra.calibration.cohort import CohortRecord, load_or_create_cohort
from rra.domain.enums import FailureCode


@dataclass(frozen=True)
class RateEstimate:
    channel: str
    failure_code: str
    n_attempts: int
    n_successes: int
    mle_rate: float
    ci_lower: float
    ci_upper: float

    @property
    def ci_margin(self) -> float:
        return (self.ci_upper - self.ci_lower) / 2


@dataclass(frozen=True)
class CalibratedParameters:
    # Auto-debit retry parameters
    p_retry_insufficient_funds: RateEstimate
    p_retry_bank_downtime: RateEstimate
    p_retry_timeout: RateEstimate

    # Digital nudge / payment link parameters
    p_nudge_insufficient_funds: RateEstimate
    p_nudge_card_expired: RateEstimate
    p_nudge_3ds_dropoff: RateEstimate
    p_nudge_timeout: RateEstimate

    # Voice telephony parameters
    p_voice_p2p_capture: RateEstimate
    p_voice_p2p_kept: RateEstimate

    # Metadata
    total_cohort_records: int
    calibration_source: str = "Razorpay Production Cohort (400 records, D2C/SaaS merchant)"


def wilson_score_interval(successes: int, trials: int, confidence: float = 0.95) -> tuple[float, float]:
    """Calculate the Wilson score confidence interval for a binomial proportion."""
    if trials == 0:
        return (0.0, 0.0)

    z = 1.95996  # 95% normal quantile
    p_hat = successes / trials
    denominator = 1 + (z ** 2) / trials
    centre_adjusted_probability = p_hat + (z ** 2) / (2 * trials)
    adjusted_std_dev = math.sqrt((p_hat * (1 - p_hat) + (z ** 2) / (4 * trials)) / trials)

    lower = (centre_adjusted_probability - z * adjusted_std_dev) / denominator
    upper = (centre_adjusted_probability + z * adjusted_std_dev) / denominator

    return (max(0.0, lower), min(1.0, upper))


class RazorpayCohortCalibrator:
    """Calibrates recovery probabilities directly from observed Razorpay cohort outcomes."""

    def __init__(self, records: list[CohortRecord] | None = None) -> None:
        self.records = records if records is not None else load_or_create_cohort()

    def estimate_rate(self, failure_code: str, channel: str) -> RateEstimate:
        """Estimate conversion rate for a given failure code and channel."""
        attempts = 0
        successes = 0

        for r in self.records:
            if r.failure_code == failure_code:
                for a in r.attempts:
                    if a.channel == channel:
                        attempts += 1
                        if a.success:
                            successes += 1

        mle = round(successes / attempts, 4) if attempts > 0 else 0.0
        low, high = wilson_score_interval(successes, attempts)

        return RateEstimate(
            channel=channel,
            failure_code=failure_code,
            n_attempts=attempts,
            n_successes=successes,
            mle_rate=mle,
            ci_lower=round(low, 4),
            ci_upper=round(high, 4),
        )

    def estimate_voice_p2p(self) -> tuple[RateEstimate, RateEstimate]:
        """Estimate voice Promise-to-Pay capture rate and kept rate."""
        calls = 0
        p2p_captured = 0
        p2p_kept = 0

        for r in self.records:
            for a in r.attempts:
                if a.channel == "voice_call" and a.p2p_captured is not None:
                    calls += 1
                    if a.p2p_captured:
                        p2p_captured += 1
                        if a.p2p_kept:
                            p2p_kept += 1

        mle_cap = round(p2p_captured / calls, 4) if calls > 0 else 0.0
        low_cap, high_cap = wilson_score_interval(p2p_captured, calls)

        mle_kept = round(p2p_kept / p2p_captured, 4) if p2p_captured > 0 else 0.0
        low_kept, high_kept = wilson_score_interval(p2p_kept, p2p_captured)

        cap_est = RateEstimate(
            channel="voice_call",
            failure_code="all_eligible_voice",
            n_attempts=calls,
            n_successes=p2p_captured,
            mle_rate=mle_cap,
            ci_lower=round(low_cap, 4),
            ci_upper=round(high_cap, 4),
        )
        kept_est = RateEstimate(
            channel="voice_call",
            failure_code="p2p_fulfillment",
            n_attempts=p2p_captured,
            n_successes=p2p_kept,
            mle_rate=mle_kept,
            ci_lower=round(low_kept, 4),
            ci_upper=round(high_kept, 4),
        )
        return cap_est, kept_est

    def calibrate(self) -> CalibratedParameters:
        """Derive all outcome model parameters from the Razorpay merchant cohort."""
        p2p_cap, p2p_kept = self.estimate_voice_p2p()

        return CalibratedParameters(
            p_retry_insufficient_funds=self.estimate_rate(FailureCode.INSUFFICIENT_FUNDS.value, "backend_retry"),
            p_retry_bank_downtime=self.estimate_rate(FailureCode.BANK_DOWNTIME.value, "backend_retry"),
            p_retry_timeout=self.estimate_rate(FailureCode.PAYMENT_TIMED_OUT.value, "backend_retry"),
            p_nudge_insufficient_funds=self.estimate_rate(FailureCode.INSUFFICIENT_FUNDS.value, "payment_link"),
            p_nudge_card_expired=self.estimate_rate(FailureCode.CARD_EXPIRED.value, "payment_link"),
            p_nudge_3ds_dropoff=self.estimate_rate(FailureCode.THREE_DS_DROPOFF.value, "payment_link"),
            p_nudge_timeout=self.estimate_rate(FailureCode.PAYMENT_TIMED_OUT.value, "payment_link"),
            p_voice_p2p_capture=p2p_cap,
            p_voice_p2p_kept=p2p_kept,
            total_cohort_records=len(self.records),
        )
