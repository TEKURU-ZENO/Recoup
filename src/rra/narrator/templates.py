"""Hardcoded deterministic fallback templates for dunning communications."""

from __future__ import annotations

from rra.domain.enums import ActionType, ChannelType
from rra.narrator.schemas import NarratorRequest, NarratorResponse


def get_fallback_message(request: NarratorRequest) -> NarratorResponse:
    """Return a guaranteed grounded fallback message for the given request context."""
    ctx = request.transaction_context
    name = ctx.customer_name
    amount = f"₹{ctx.amount_due_inr:,.2f}"
    link = ctx.payment_link or f"https://rzp.io/i/{ctx.subscription_id}"

    if ctx.action_type == ActionType.METHOD_SWITCH_LINK:
        body = (
            f"Hi {name}, your recurring subscription ({ctx.subscription_id}) payment of {amount} "
            f"could not be processed as your card has expired. Please update your payment method here: {link}"
        )
    elif ctx.action_type == ActionType.FRICTION_REDUCTION_LINK:
        body = (
            f"Hi {name}, payment of {amount} for subscription {ctx.subscription_id} was incomplete. "
            f"Complete your payment in 1 click: {link}"
        )
    else:
        body = (
            f"Hi {name}, your payment of {amount} for subscription {ctx.subscription_id} is pending. "
            f"You can complete it using this secure link: {link}"
        )

    return NarratorResponse(
        message_body=body,
        subject_line=f"Payment Update for {ctx.subscription_id}",
        channel=ChannelType.WHATSAPP if ctx.action_type != ActionType.SMS_NUDGE else ChannelType.SMS,
        language=request.policy_constraints.language,
        model_id="deterministic_template_fallback",
        grounding_passed=True,
    )
