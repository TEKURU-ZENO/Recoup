"""Benchmark metrics calculation and economic accounting.

Includes:
- Recovery rates (gross and net)
- MDR fees (2.0% on successful settlements)
- Channel execution costs (SMS ₹0.25, WhatsApp ₹0.50, Voice ₹5.00, Retry ₹0.00)
- Contact fatigue churn penalty (1.5% churn hazard × ₹3,000 LTV per excess contact)
- Waste spent chasing structurally unrecoverable accounts
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rra.domain.enums import ActionType, CaseStatus, ChannelType, FailureCode
from rra.domain.models import Action, Case, Outcome

# Cost constants (in integer paise)
MDR_RATE = 0.02  # 2.0% Merchant Discount Rate on recovered revenue
COST_BACKEND_RETRY_PAISE = 0  # Razorpay does not charge gateway fees on failed retries
COST_SMS_PAISE = 25  # ₹0.25 per SMS
COST_WHATSAPP_PAISE = 50  # ₹0.50 per WhatsApp template
COST_VOICE_CALL_PAISE = 500  # ₹5.00 per outbound LiveKit/Twilio voice call
COST_LINK_PAISE = 0  # Hosted payment link generation (zero marginal gateway fee)

# Churn fatigue model
CUSTOMER_LTV_PAISE = 300000  # ₹3,000 average subscription Lifetime Value
CHURN_HAZARD_PER_EXCESS_CONTACT = 0.015  # 1.5% voluntary cancellation probability per excess contact
EXPECTED_CHURN_COST_PER_EXCESS_CONTACT_PAISE = int(CUSTOMER_LTV_PAISE * CHURN_HAZARD_PER_EXCESS_CONTACT)  # ₹45.00


def is_declined_chase(case: Case, history: list[tuple[Action, Outcome]]) -> bool:
    """Predicate: did the arm *choose* not to pursue this case?

    A declined chase means the arm returned None before executing any action
    on a case that still has outstanding revenue. This measures agent judgment,
    not case properties — NaiveUnbounded should decline 0 cases because it
    always attempts retries regardless of failure code.
    """
    executed_actions = [act for act, _ in history if act.executed_at is not None]
    if len(executed_actions) == 0 and case.status != CaseStatus.SETTLED:
        return True
    return False


@dataclass
class ArmRunMetrics:
    """Metrics compiled for a single arm over a portfolio run."""

    arm_name: str
    seed: int
    total_cases: int = 0
    total_revenue_at_risk_paise: int = 0
    total_recovered_paise: int = 0
    recovery_rate_pct: float = 0.0
    recovered_cases_count: int = 0
    case_resolution_rate_pct: float = 0.0
    retries_executed: int = 0
    interventions_sent: dict[str, int] = field(default_factory=dict)
    declined_chases: int = 0
    mean_days_to_settle: float = 0.0
    guard_violations: int = 0
    failure_mode_recovered: dict[str, int] = field(default_factory=dict)
    failure_mode_total: dict[str, int] = field(default_factory=dict)

    # Economics metrics (in integer paise)
    mdr_fees_paise: int = 0
    channel_costs_paise: int = 0
    churn_costs_paise: int = 0
    waste_on_unrecoverable_paise: int = 0
    net_recovered_paise: int = 0
    roi_multiple: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "arm_name": self.arm_name,
            "seed": self.seed,
            "total_cases": self.total_cases,
            "total_revenue_at_risk_inr": self.total_revenue_at_risk_paise / 100,
            "total_recovered_inr": self.total_recovered_paise / 100,
            "recovery_rate_pct": round(self.recovery_rate_pct, 2),
            "retries_executed": self.retries_executed,
            "interventions_sent": self.interventions_sent,
            "declined_chases": self.declined_chases,
            "mean_days_to_settle": round(self.mean_days_to_settle, 2),
            "guard_violations": self.guard_violations,
            "mdr_fees_inr": self.mdr_fees_paise / 100,
            "channel_costs_inr": self.channel_costs_paise / 100,
            "churn_costs_inr": self.churn_costs_paise / 100,
            "waste_on_unrecoverable_inr": self.waste_on_unrecoverable_paise / 100,
            "net_recovered_inr": self.net_recovered_paise / 100,
            "roi_multiple": round(self.roi_multiple, 2),
        }


def compute_metrics(
    arm_name: str,
    seed: int,
    results: list[tuple[Case, list[tuple[Action, Outcome]]]],
) -> ArmRunMetrics:
    """Calculate aggregate metrics and economics from a portfolio simulation run."""
    metrics = ArmRunMetrics(
        arm_name=arm_name,
        seed=seed,
        total_cases=len(results),
        interventions_sent={"sms": 0, "whatsapp": 0, "voice": 0, "email": 0, "link": 0},
    )

    settle_times_days: list[float] = []

    for case, history in results:
        metrics.total_revenue_at_risk_paise += case.amount_due_paise
        fc = case.failure_code.value
        metrics.failure_mode_total[fc] = metrics.failure_mode_total.get(fc, 0) + 1

        # Check declined chase predicate
        if is_declined_chase(case, history):
            metrics.declined_chases += 1

        is_structurally_unrecoverable = case.failure_code in (
            FailureCode.MANDATE_REVOKED,
            FailureCode.INPUT_VALIDATION_FAILED,
        )

        case_recovered = False
        case_customer_contacts = 0

        for action, outcome in history:
            if action.metadata.get("guard_violation"):
                metrics.guard_violations += 1

            act_cost_paise = 0

            if action.action_type == ActionType.BACKEND_RETRY:
                metrics.retries_executed += 1
                act_cost_paise = COST_BACKEND_RETRY_PAISE
            elif action.action_type == ActionType.SMS_NUDGE:
                metrics.interventions_sent["sms"] += 1
                act_cost_paise = COST_SMS_PAISE
                case_customer_contacts += 1
            elif action.action_type == ActionType.WHATSAPP_NUDGE:
                metrics.interventions_sent["whatsapp"] += 1
                act_cost_paise = COST_WHATSAPP_PAISE
                case_customer_contacts += 1
            elif action.action_type == ActionType.VOICE_CALL:
                metrics.interventions_sent["voice"] += 1
                act_cost_paise = COST_VOICE_CALL_PAISE
                case_customer_contacts += 1
            elif action.action_type in (
                ActionType.PAYMENT_LINK,
                ActionType.METHOD_SWITCH_LINK,
                ActionType.FRICTION_REDUCTION_LINK,
            ):
                metrics.interventions_sent["link"] += 1
                act_cost_paise = COST_LINK_PAISE
                case_customer_contacts += 1

            metrics.channel_costs_paise += act_cost_paise

            # If spent on structurally unrecoverable account, count as pure waste
            if is_structurally_unrecoverable:
                metrics.waste_on_unrecoverable_paise += act_cost_paise

            if outcome and outcome.success and not case_recovered:
                case_recovered = True
                metrics.total_recovered_paise += outcome.amount_recovered_paise
                metrics.failure_mode_recovered[fc] = (
                    metrics.failure_mode_recovered.get(fc, 0) + 1
                )
                settle_days = (outcome.timestamp - case.created_at).total_seconds() / 86400.0
                settle_times_days.append(max(0.0, settle_days))

        # Contact fatigue calculation: contacts beyond 2 (or contact on DND)
        excess_contacts = max(0, case_customer_contacts - 2)
        if case.is_dnd and case_customer_contacts > 0:
            excess_contacts = case_customer_contacts  # All contacts to DND customer are unwanted

        metrics.churn_costs_paise += excess_contacts * EXPECTED_CHURN_COST_PER_EXCESS_CONTACT_PAISE

        if case_recovered:
            metrics.recovered_cases_count += 1

    if metrics.total_cases > 0:
        metrics.case_resolution_rate_pct = (metrics.recovered_cases_count / metrics.total_cases) * 100.0

    # Financial totals
    metrics.mdr_fees_paise = int(metrics.total_recovered_paise * MDR_RATE)
    total_spend_paise = metrics.mdr_fees_paise + metrics.channel_costs_paise + metrics.churn_costs_paise
    metrics.net_recovered_paise = metrics.total_recovered_paise - total_spend_paise

    if total_spend_paise > 0:
        metrics.roi_multiple = metrics.net_recovered_paise / total_spend_paise

    if metrics.total_revenue_at_risk_paise > 0:
        metrics.recovery_rate_pct = (
            metrics.total_recovered_paise / metrics.total_revenue_at_risk_paise
        ) * 100.0

    if settle_times_days:
        metrics.mean_days_to_settle = sum(settle_times_days) / len(settle_times_days)

    return metrics
