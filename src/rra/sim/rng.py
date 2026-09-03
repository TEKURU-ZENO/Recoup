"""Deterministic random number generation for common random numbers (CRN).

This module is the mechanism behind fair benchmark comparisons. Both arms
working the same case on the same action type at the same ordinal get the
same uniform draw. They differ only in the probability that draw is
compared against, which is driven by *when* the action was taken.

The draw is keyed on (seed, case_id, action_type, ordinal_within_that_type)
so that a retry draw is always compared against a retry draw, even when
arms diverge in their action sequences.
"""

import hashlib
import struct


def draw_for(
    seed: int,
    case_id: str,
    action_type: str,
    ordinal: int,
) -> float:
    """Return a deterministic uniform in [0, 1) for the given parameters.

    Uses SHA-256 to map (seed, case_id, action_type, ordinal) to a
    reproducible pseudo-random value. This ensures:
    - Same seed + case + action_type + ordinal -> identical draw across arms
    - Different action types get independent draws (no cross-contamination)
    - Ordinal is within-type, not global (retry #2 != nudge #2)

    Args:
        seed: Global benchmark seed.
        case_id: The case being worked.
        action_type: The type of action (e.g., 'backend_retry', 'sms_nudge').
        ordinal: The 0-based count of this action type for this case.

    Returns:
        A float in [0, 1).
    """
    key = f"{seed}|{case_id}|{action_type}|{ordinal}"
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    # Take first 8 bytes as a uint64, divide by max uint64
    value = struct.unpack("!Q", digest[:8])[0]
    return value / (2**64)
