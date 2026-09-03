"""Pydantic schemas for the fenced LLM narrator request and response payloads."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from rra.domain.enums import ActionType, ChannelType


class TransactionContext(BaseModel):
    """Contextual metadata passed into the fenced narrator prompt."""

    subscription_id: str
    customer_name: str
    amount_due_inr: float
    amount_due_paise: int
    failure_reason: str
    attempt_count: int
    max_attempts: int = 3
    next_scheduled_retry: str | None = None
    action_type: ActionType
    payment_link: str | None = None


class PolicyConstraints(BaseModel):
    """Rigid policy bounds passed to the LLM."""

    allowed_actions: list[str] = Field(
        default_factory=lambda: ["notify_upcoming_retry", "offer_payment_link"]
    )
    prohibited_actions: list[str] = Field(
        default_factory=lambda: [
            "offer_discount",
            "cancel_subscription",
            "threaten_legal",
            "waive_fees",
        ]
    )
    tone: str = "empathetic_professional"
    language: str = "hinglish"


class NarratorRequest(BaseModel):
    """Input payload envelope for the narrator."""

    transaction_context: TransactionContext
    policy_constraints: PolicyConstraints


class NarratorResponse(BaseModel):
    """Strict JSON schema output from the narrator model."""

    message_body: str
    subject_line: str | None = None
    channel: ChannelType
    language: str = "hinglish"
    model_id: str = "gpt-4o-mini-2024-07-18"
    prompt_hash: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    grounding_passed: bool = True
