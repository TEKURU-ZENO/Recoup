"""Benchmark arms implementation with policy and guard enforcement."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol

from rra.domain.enums import ActionType, ChannelType
from rra.domain.models import Action, Case, Outcome
from rra.engine.guards import evaluate as evaluate_guards
from rra.engine.policy import next_action as policy_next_action


class Arm(Protocol):
    """Protocol for recovery decision arms."""

    @property
    def name(self) -> str:
        ...

    def decide(
        self,
        case: Case,
        history: list[tuple[Action, Outcome]],
        now: datetime,
    ) -> Action | None:
        ...


class NaiveUnboundedArm:
    """Fixed-interval dunning schedule (24h/48h/72h) with generic nudges.

    Ignores failure codes, bank downtime, salary proximity, TRAI windows, DND, etc.
    Executes fixed retries and nudges regardless of guards.
    """

    def __init__(self, name: str = "NaiveUnbounded") -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def decide(
        self,
        case: Case,
        history: list[tuple[Action, Outcome]],
        now: datetime,
    ) -> Action | None:
        if case.status in ("settled", "halted", "declined"):
            return None

        past_actions = [act for act, _ in history if act.executed_at is not None]
        retry_count = sum(1 for act in past_actions if act.action_type == ActionType.BACKEND_RETRY)
        nudge_count = sum(
            1
            for act in past_actions
            if act.action_type in (ActionType.SMS_NUDGE, ActionType.WHATSAPP_NUDGE)
        )

        last_action_time = past_actions[-1].executed_at if past_actions else case.created_at

        proposed: Action | None = None
        if retry_count < 3:
            scheduled_at = max(now, last_action_time + timedelta(hours=24))
            proposed = Action(
                case_id=case.case_id,
                action_type=ActionType.BACKEND_RETRY,
                scheduled_at=scheduled_at,
                rule_id="NAIVE_FIXED_24H_RETRY",
            )
        elif nudge_count < 2:
            scheduled_at = max(now, last_action_time + timedelta(hours=48))
            proposed = Action(
                case_id=case.case_id,
                action_type=ActionType.SMS_NUDGE,
                channel=ChannelType.SMS,
                scheduled_at=scheduled_at,
                rule_id="NAIVE_FIXED_48H_NUDGE",
            )

        if proposed is None:
            return None

        # Check guards for audit/reporting purposes (but DO NOT enforce)
        decision = evaluate_guards(case, proposed, history, now)
        if not decision.allowed:
            proposed.metadata["guard_violation"] = decision.rule_id

        return proposed


class NaiveBoundedArm:
    """Fixed 24/48/72h timing, with guard enforcement (digital channels only)."""

    def __init__(self, name: str = "NaiveBounded") -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def decide(
        self,
        case: Case,
        history: list[tuple[Action, Outcome]],
        now: datetime,
    ) -> Action | None:
        return policy_next_action(
            case=case, history=history, now=now, use_smart_scheduling=False, voice_enabled=False
        )


class SmartBoundedArm:
    """Smart contextual policy with full guard enforcement (digital channels only)."""

    def __init__(self, name: str = "SmartBounded") -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def decide(
        self,
        case: Case,
        history: list[tuple[Action, Outcome]],
        now: datetime,
    ) -> Action | None:
        return policy_next_action(
            case=case, history=history, now=now, use_smart_scheduling=True, voice_enabled=False
        )


class SmartBoundedVoiceArm:
    """Smart contextual policy + guards + LiveKit voice intercept on high-value cases (>₹5,000)."""

    def __init__(self, name: str = "SmartBoundedVoice") -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def decide(
        self,
        case: Case,
        history: list[tuple[Action, Outcome]],
        now: datetime,
    ) -> Action | None:
        return policy_next_action(
            case=case, history=history, now=now, use_smart_scheduling=True, voice_enabled=True
        )
