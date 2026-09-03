"""Domain enumerations for the Revenue Recovery Agent.

Pure types, zero dependencies beyond the standard library.
"""

from enum import StrEnum


class FailureCode(StrEnum):
    """Root cause classification of a payment failure."""

    INSUFFICIENT_FUNDS = "insufficient_funds"
    BANK_DOWNTIME = "bank_downtime"
    CARD_EXPIRED = "card_expired"
    THREE_DS_DROPOFF = "3ds_dropoff"
    MANDATE_REVOKED = "mandate_revoked"
    PAYMENT_TIMED_OUT = "payment_timed_out"
    INPUT_VALIDATION_FAILED = "input_validation_failed"


class EscalationLevel(StrEnum):
    """FSM states for the recovery lifecycle."""

    INGESTED = "ingested"
    SMART_RETRY = "smart_retry"
    DIGITAL_NUDGE = "digital_nudge"
    VOICE_INTERCEPT = "voice_intercept"
    TERMINAL_HALT = "terminal_halt"


class CaseStatus(StrEnum):
    """Overall case lifecycle status."""

    ACTIVE = "active"
    SETTLED = "settled"
    P2P_SCHEDULED = "p2p_scheduled"
    HALTED = "halted"
    DECLINED = "declined"


class ChannelType(StrEnum):
    """Communication channel types."""

    SMS = "sms"
    WHATSAPP = "whatsapp"
    VOICE = "voice"
    EMAIL = "email"
    PAYMENT_LINK = "payment_link"


class ActionType(StrEnum):
    """Types of recovery actions the system can take."""

    BACKEND_RETRY = "backend_retry"
    PAYMENT_LINK = "payment_link"
    METHOD_SWITCH_LINK = "method_switch_link"
    FRICTION_REDUCTION_LINK = "friction_reduction_link"
    SMS_NUDGE = "sms_nudge"
    WHATSAPP_NUDGE = "whatsapp_nudge"
    VOICE_CALL = "voice_call"
    HALT = "halt"


class InstrumentType(StrEnum):
    """Payment instrument types for recurring payments."""

    UPI_AUTOPAY = "upi_autopay"
    CARD_RECURRING = "card_recurring"
    EMANDATE = "emandate"
