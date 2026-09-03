"""Benchmark simulation runner.

The ONLY module permitted to import both rra.sim and rra.engine.
Executes an Arm on a generated portfolio over a 30-day virtual time horizon,
using common random numbers (CRN) for fair comparison.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from rra.domain.enums import CaseStatus
from rra.domain.models import Action, Case, Outcome
from rra.sim.clock import VirtualClock
from rra.sim.downtime import DowntimeCalendar
from rra.sim.outcome_model import draw as resolve_outcome
from rra.sim.portfolio import generate_portfolio
from rra.sim.rng import draw_for

if TYPE_CHECKING:
    from rra.bench.arms import Arm
    from rra.bench.metrics import ArmRunMetrics


def run_simulation(
    arm: Arm,
    seed: int,
    n_cases: int = 215,
    horizon_days: int = 30,
    base_time: datetime | None = None,
) -> tuple[list[tuple[Case, list[tuple[Action, Outcome]]]], ArmRunMetrics]:
    """Run a full simulation for a single arm on a portfolio.

    Args:
        arm: The recovery decision arm to evaluate.
        seed: Benchmark seed for portfolio generation and CRN draws.
        n_cases: Number of cases in portfolio (default: 215).
        horizon_days: Maximum virtual time horizon per case (default: 30 days).
        base_time: Simulation start time (UTC-aware).

    Returns:
        Tuple of (case_results, metrics).
    """
    from rra.bench.metrics import compute_metrics

    if base_time is None:
        base_time = datetime(2026, 4, 1, 0, 0, 0, tzinfo=timezone.utc)

    # 1. Generate portfolio sealed by seed
    portfolio = generate_portfolio(seed=seed, n=n_cases, base_time=base_time)

    # 2. Instantiate downtime calendar sealed by seed
    downtime_cal = DowntimeCalendar(seed=seed, start=base_time, horizon_days=horizon_days)

    results: list[tuple[Case, list[tuple[Action, Outcome]]]] = []

    # 3. Simulate each case independently
    for original_case in portfolio:
        # Clone case so arms don't mutate shared objects across runs
        case = original_case.model_copy(deep=True)
        history: list[tuple[Action, Outcome]] = []

        clock = VirtualClock(start=case.created_at)
        max_time = case.created_at + timedelta(days=horizon_days)

        # Track per-action-type ordinal counts for CRN keying
        action_ordinals: dict[str, int] = {}

        while clock.now < max_time and case.status == CaseStatus.ACTIVE:
            # Ask arm for next action
            action = arm.decide(case=case, history=history, now=clock.now)
            if action is None:
                break

            # If action is scheduled after simulation horizon, drop it
            if action.scheduled_at > max_time:
                break

            # Advance virtual clock to action execution time
            clock.advance_to(action.scheduled_at)

            # Determine ordinal count for this action type
            act_type_str = action.action_type.value
            ordinal = action_ordinals.get(act_type_str, 0)
            action_ordinals[act_type_str] = ordinal + 1

            import hashlib
            act_id_hash = hashlib.sha256(
                f"{seed}|{case.case_id}|{act_type_str}|{ordinal}".encode()
            ).hexdigest()[:12]
            action_id = f"act_{act_id_hash}"
            action.action_id = action_id

            # Common random number draw sealed by (seed, case_id, action_type, ordinal)
            uniform = draw_for(
                seed=seed,
                case_id=case.case_id,
                action_type=act_type_str,
                ordinal=ordinal,
            )

            # Resolve through oracle outcome model
            action.executed_at = clock.now
            outcome = resolve_outcome(
                case=case,
                action_type=action.action_type,
                at=clock.now,
                uniform=uniform,
                downtime_calendar=downtime_cal,
                action_id=action_id,
            )

            action.result = "success" if outcome.success else "failed"
            history.append((action, outcome))

            # Update case state on success
            if outcome.success:
                case.status = CaseStatus.SETTLED
                case.updated_at = clock.now
                break

        results.append((case, history))

    metrics = compute_metrics(arm_name=arm.name, seed=seed, results=results)
    return results, metrics
