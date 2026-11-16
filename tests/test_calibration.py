"""Unit tests for the Razorpay merchant cohort calibration pipeline."""

from rra.calibration.calibrator import (
    CalibratedParameters,
    RateEstimate,
    RazorpayCohortCalibrator,
    wilson_score_interval,
)
from rra.calibration.cohort import (
    CohortRecord,
    generate_razorpay_merchant_cohort,
    load_or_create_cohort,
)
from rra.domain.enums import FailureCode
from rra.sim.outcome_model import (
    _BASE_RETRY_PROB_INSUFFICIENT,
    _NUDGE_CONVERSION_CARD_EXPIRED,
    _POST_OUTAGE_RETRY_PROB,
)


class TestWilsonScoreInterval:
    """Test mathematical properties of Wilson score confidence interval."""

    def test_zero_trials_returns_zero(self):
        assert wilson_score_interval(0, 0) == (0.0, 0.0)

    def test_interval_bounds_unit_interval(self):
        low, high = wilson_score_interval(10, 50)
        assert 0.0 <= low <= high <= 1.0

    def test_mle_is_contained_in_interval(self):
        trials = 100
        for succ in [10, 25, 50, 75, 90]:
            low, high = wilson_score_interval(succ, trials)
            mle = succ / trials
            assert low <= mle <= high

    def test_larger_sample_narrows_interval(self):
        low_small, high_small = wilson_score_interval(25, 100)
        low_large, high_large = wilson_score_interval(250, 1000)
        width_small = high_small - low_small
        width_large = high_large - low_large
        assert width_large < width_small


class TestRazorpayCohortGeneration:
    """Test structure and distribution of the 400-case merchant cohort."""

    def test_cohort_size_is_400(self):
        cohort = generate_razorpay_merchant_cohort()
        assert len(cohort) == 400

    def test_taxonomy_distribution(self):
        cohort = generate_razorpay_merchant_cohort()
        fc_counts = {}
        for r in cohort:
            fc_counts[r.failure_code] = fc_counts.get(r.failure_code, 0) + 1

        assert fc_counts[FailureCode.INSUFFICIENT_FUNDS.value] == 176  # 44%
        assert fc_counts[FailureCode.BANK_DOWNTIME.value] == 88        # 22%
        assert fc_counts[FailureCode.CARD_EXPIRED.value] == 52        # 13%
        assert fc_counts[FailureCode.THREE_DS_DROPOFF.value] == 36    # 9%
        assert fc_counts[FailureCode.MANDATE_REVOKED.value] == 28     # 7%
        assert fc_counts[FailureCode.PAYMENT_TIMED_OUT.value] == 12   # 3%
        assert fc_counts["unmapped"] == 8                             # 2%

    def test_structural_zeros_in_cohort(self):
        cohort = generate_razorpay_merchant_cohort()
        for r in cohort:
            if r.failure_code == FailureCode.MANDATE_REVOKED.value:
                assert all(not a.success for a in r.attempts)
            if r.failure_code == FailureCode.CARD_EXPIRED.value:
                retry_attempts = [a for a in r.attempts if a.channel == "backend_retry"]
                assert all(not a.success for a in retry_attempts)


class TestCalibrator:
    """Test parameter extraction from the Razorpay cohort."""

    def test_calibration_generates_all_parameters(self):
        cohort = generate_razorpay_merchant_cohort()
        calibrator = RazorpayCohortCalibrator(cohort)
        params = calibrator.calibrate()

        assert isinstance(params, CalibratedParameters)
        assert params.total_cohort_records == 400

        # Auto-debit retries
        assert params.p_retry_insufficient_funds.n_attempts == 176
        assert params.p_retry_insufficient_funds.mle_rate == 0.250
        assert params.p_retry_bank_downtime.n_attempts == 88
        assert params.p_retry_bank_downtime.mle_rate == 0.7045

        # Digital links
        assert params.p_nudge_card_expired.n_attempts == 52
        assert params.p_nudge_card_expired.mle_rate == 0.1731
        assert params.p_nudge_3ds_dropoff.n_attempts == 36
        assert params.p_nudge_3ds_dropoff.mle_rate == 0.2222

        # Telephony
        assert params.p_voice_p2p_capture.n_attempts > 0
        assert 0.40 <= params.p_voice_p2p_capture.mle_rate <= 0.70
        assert 0.60 <= params.p_voice_p2p_kept.mle_rate <= 0.85

    def test_outcome_model_constants_match_calibrated_estimates(self):
        calibrator = RazorpayCohortCalibrator()
        params = calibrator.calibrate()

        assert _BASE_RETRY_PROB_INSUFFICIENT == params.p_retry_insufficient_funds.mle_rate
        assert _POST_OUTAGE_RETRY_PROB == params.p_retry_bank_downtime.mle_rate
        assert _NUDGE_CONVERSION_CARD_EXPIRED == params.p_nudge_card_expired.mle_rate
