"""Synthetic portfolio generator for benchmark simulation.

Generates deterministic batches of failed payment cases with:
- Log-normal amounts (~₹300-₹50,000, median ~₹1,200)
- Realistic failure code distribution
- Instrument type mix
- Customer metadata (phone, DND, language)

All randomness is seeded for reproducibility.
"""

from __future__ import annotations

import hashlib
import math
import struct
from datetime import datetime, timedelta, timezone

from rra.domain.enums import (
    CaseStatus,
    EscalationLevel,
    FailureCode,
    InstrumentType,
)
from rra.domain.models import Case


# ---------------------------------------------------------------------------
# Distribution constants — all documented in docs/assumptions.md
# ---------------------------------------------------------------------------

# Log-normal amount distribution (in INR)
# mu and sigma for log(amount_inr)
# Target: median ~₹1,200, range ~₹300-₹50,000
_AMOUNT_MU = 7.09  # ln(1200) ≈ 7.09 [judgment]
_AMOUNT_SIGMA = 1.0  # [judgment] - gives good spread
_AMOUNT_MIN_PAISE = 30000  # ₹300 floor
_AMOUNT_MAX_PAISE = 5000000  # ₹50,000 cap

# Failure code distribution
_FAILURE_DISTRIBUTION: list[tuple[FailureCode, float]] = [
    (FailureCode.INSUFFICIENT_FUNDS, 0.42),
    (FailureCode.BANK_DOWNTIME, 0.21),
    (FailureCode.CARD_EXPIRED, 0.14),
    (FailureCode.THREE_DS_DROPOFF, 0.11),
    (FailureCode.MANDATE_REVOKED, 0.08),
    (FailureCode.PAYMENT_TIMED_OUT, 0.04),
]

# Instrument type distribution
_INSTRUMENT_DISTRIBUTION: list[tuple[InstrumentType, float]] = [
    (InstrumentType.UPI_AUTOPAY, 0.50),
    (InstrumentType.CARD_RECURRING, 0.30),
    (InstrumentType.EMANDATE, 0.20),
]

# DND prevalence
_DND_RATE = 0.15  # [judgment] - 15% of customers on DND

# Phone presence rate
_PHONE_PRESENT_RATE = 0.92  # [judgment]

# Customer names pool (common Indian names)
_FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun",
    "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan",
    "Ananya", "Diya", "Priya", "Saanvi", "Aanya",
    "Isha", "Kavya", "Riya", "Meera", "Neha",
    "Rohan", "Karthik", "Rahul", "Amit", "Vijay",
    "Sneha", "Pooja", "Deepika", "Lakshmi", "Srishti",
]

_LAST_NAMES = [
    "Sharma", "Patel", "Singh", "Kumar", "Gupta",
    "Reddy", "Nair", "Joshi", "Verma", "Iyer",
    "Chauhan", "Desai", "Mehta", "Rao", "Pandey",
    "Mishra", "Chopra", "Saxena", "Menon", "Pillai",
]

_LANGUAGES = ["hinglish", "hindi", "english"]
_LANGUAGE_WEIGHTS = [0.55, 0.30, 0.15]


# ---------------------------------------------------------------------------
# Seeded RNG helpers
# ---------------------------------------------------------------------------

def _seeded_float(seed: int, key: str) -> float:
    """Deterministic float in [0, 1) from seed and key."""
    digest = hashlib.sha256(f"{seed}|{key}".encode()).digest()
    return struct.unpack("!Q", digest[:8])[0] / (2**64)


def _seeded_int(seed: int, key: str, low: int, high: int) -> int:
    """Deterministic int in [low, high) from seed and key."""
    return low + int(_seeded_float(seed, key) * (high - low))


def _seeded_choice(
    seed: int,
    key: str,
    items: list,
    weights: list[float] | None = None,
) -> object:
    """Deterministic weighted choice from a list."""
    draw = _seeded_float(seed, key)
    if weights is None:
        idx = int(draw * len(items))
        return items[min(idx, len(items) - 1)]

    cumulative = 0.0
    for i, w in enumerate(weights):
        cumulative += w
        if draw < cumulative:
            return items[i]
    return items[-1]


def _seeded_lognormal(seed: int, key: str, mu: float, sigma: float) -> float:
    """Deterministic log-normal sample using Box-Muller transform."""
    u1 = max(1e-10, _seeded_float(seed, f"{key}_u1"))  # avoid log(0)
    u2 = _seeded_float(seed, f"{key}_u2")
    z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
    return math.exp(mu + sigma * z)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_portfolio(
    seed: int,
    n: int = 215,
    base_time: datetime | None = None,
) -> list[Case]:
    """Generate a deterministic portfolio of failed payment cases.

    Args:
        seed: Random seed for reproducibility.
        n: Number of cases to generate (default: 215).
        base_time: Start time for case creation timestamps.
                   Defaults to 2026-04-01 00:00:00 UTC.

    Returns:
        A list of n Case objects with realistic distributions.
    """
    if base_time is None:
        base_time = datetime(2026, 4, 1, 0, 0, 0, tzinfo=timezone.utc)
    elif base_time.tzinfo is None:
        raise ValueError("base_time must be timezone-aware")

    cases: list[Case] = []
    failure_codes = [fc for fc, _ in _FAILURE_DISTRIBUTION]
    failure_weights = [w for _, w in _FAILURE_DISTRIBUTION]
    instrument_types = [it for it, _ in _INSTRUMENT_DISTRIBUTION]
    instrument_weights = [w for _, w in _INSTRUMENT_DISTRIBUTION]

    for i in range(n):
        case_key = f"case_{i}"

        # Failure code
        failure_code = _seeded_choice(
            seed, f"{case_key}_failure", failure_codes, failure_weights
        )

        # Amount (log-normal in INR, stored as paise)
        amount_inr = _seeded_lognormal(
            seed, f"{case_key}_amount", _AMOUNT_MU, _AMOUNT_SIGMA
        )
        amount_paise = int(round(amount_inr * 100))
        amount_paise = max(_AMOUNT_MIN_PAISE, min(_AMOUNT_MAX_PAISE, amount_paise))

        # Instrument type
        instrument = _seeded_choice(
            seed, f"{case_key}_instrument", instrument_types, instrument_weights
        )

        # Customer name
        first = _seeded_choice(seed, f"{case_key}_first", _FIRST_NAMES)
        last = _seeded_choice(seed, f"{case_key}_last", _LAST_NAMES)

        # Phone
        has_phone = _seeded_float(seed, f"{case_key}_phone") < _PHONE_PRESENT_RATE
        phone = None
        if has_phone:
            phone_num = _seeded_int(seed, f"{case_key}_phone_num", 7000000000, 9999999999)
            phone = f"+91{phone_num}"

        # DND
        is_dnd = _seeded_float(seed, f"{case_key}_dnd") < _DND_RATE

        # Language
        language = _seeded_choice(
            seed, f"{case_key}_lang", _LANGUAGES, _LANGUAGE_WEIGHTS
        )

        # Creation time: spread across first 48h of the simulation
        time_offset_hours = _seeded_float(seed, f"{case_key}_time") * 48
        created_at = base_time + timedelta(hours=time_offset_hours)

        # Subscription ID
        sub_hash = hashlib.sha256(
            f"{seed}|{case_key}_sub".encode()
        ).hexdigest()[:12]
        subscription_id = f"sub_{sub_hash}"

        # Case ID
        case_hash = hashlib.sha256(
            f"{seed}|{case_key}_id".encode()
        ).hexdigest()[:12]
        case_id = f"case_{case_hash}"

        case = Case(
            case_id=case_id,
            subscription_id=subscription_id,
            customer_name=f"{first} {last}",
            amount_due_paise=amount_paise,
            failure_code=failure_code,
            instrument_type=instrument,
            status=CaseStatus.ACTIVE,
            escalation_level=EscalationLevel.INGESTED,
            attempt_count=0,
            phone_number=phone,
            is_dnd=is_dnd,
            is_opted_out=False,
            language_preference=language,
            created_at=created_at,
            updated_at=created_at,
        )
        cases.append(case)

    return cases
