"""Domain models for the Revenue Recovery Agent.

All monetary values are stored in integer paise (1 INR = 100 paise)
to avoid floating-point rounding errors.

All timestamps are UTC-enforced timezone-aware datetimes.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from rra.domain.enums import (
    ActionType,
    CaseStatus,
    ChannelType,
    EscalationLevel,
    FailureCode,
    InstrumentType,
)


def _utc_now() -> datetime:
    """Return the current UTC time, timezone-aware."""
    return datetime.now(timezone.utc)


def _new_id(prefix: str) -> str:
    """Generate a prefixed unique ID."""
    return f"{prefix}_{uuid4().hex[:12]}"


class Case(BaseModel):
    """A payment recovery case tracking a single failed subscription charge.

    Amounts are in integer paise (1 INR = 100 paise).
    """

    case_id: str = Field(default_factory=lambda: _new_id("case"))
    subscription_id: str
    customer_name: str
    amount_due_paise: int = Field(gt=0, description="Amount in paise (1 INR = 100 paise)")
    failure_code: FailureCode
    instrument_type: InstrumentType = InstrumentType.UPI_AUTOPAY
    status: CaseStatus = CaseStatus.ACTIVE
    escalation_level: EscalationLevel = EscalationLevel.INGESTED
    attempt_count: int = Field(default=0, ge=0)
    phone_number: str | None = None
    is_dnd: bool = False
    is_opted_out: bool = False
    language_preference: str = "hinglish"
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    model_config = {"frozen": False}

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _enforce_utc(cls, v: datetime) -> datetime:
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError("Naive datetimes are not allowed — use UTC-aware datetimes")
        return v

    @property
    def amount_inr(self) -> float:
        """Convenience: amount in INR (for display only, never for arithmetic)."""
        return self.amount_due_paise / 100


class Action(BaseModel):
    """A single recovery action taken on a case."""

    action_id: str = Field(default_factory=lambda: _new_id("act"))
    case_id: str
    action_type: ActionType
    channel: ChannelType | None = None
    rule_id: str | None = None
    scheduled_at: datetime
    executed_at: datetime | None = None
    result: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": False}

    @field_validator("scheduled_at", "executed_at", mode="before")
    @classmethod
    def _enforce_utc(cls, v: datetime | None) -> datetime | None:
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError("Naive datetimes are not allowed — use UTC-aware datetimes")
        return v


class Outcome(BaseModel):
    """The result of resolving an action through the outcome model."""

    case_id: str
    action_id: str
    success: bool
    amount_recovered_paise: int = Field(ge=0)
    timestamp: datetime

    @field_validator("timestamp", mode="before")
    @classmethod
    def _enforce_utc(cls, v: datetime) -> datetime:
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError("Naive datetimes are not allowed — use UTC-aware datetimes")
        return v


class AuditRecord(BaseModel):
    """Append-only, hash-chained audit record.

    Frozen after creation. Each record carries sha256(previous_record)
    to form a tamper-evident chain.
    """

    audit_id: str = Field(default_factory=lambda: _new_id("aud"))
    timestamp_utc: datetime = Field(default_factory=_utc_now)
    subscription_id: str
    actor: str
    policy_version: str = "v2026.1.0"
    rule_triggered: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    execution_payload: dict[str, Any] = Field(default_factory=dict)
    compliance_check: dict[str, Any] = Field(default_factory=dict)
    previous_hash: str = Field(default="genesis")
    record_hash: str = Field(default="")

    model_config = {"frozen": True}

    @field_validator("timestamp_utc", mode="before")
    @classmethod
    def _enforce_utc(cls, v: datetime) -> datetime:
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError("Naive datetimes are not allowed — use UTC-aware datetimes")
        return v

    @model_validator(mode="after")
    def _compute_hash(self) -> AuditRecord:
        """Compute the record hash from all fields except record_hash itself."""
        data = self.model_dump(exclude={"record_hash"})
        # Serialize deterministically
        canonical = json.dumps(data, sort_keys=True, default=str)
        computed = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        # Use object.__setattr__ because the model is frozen
        object.__setattr__(self, "record_hash", computed)
        return self
