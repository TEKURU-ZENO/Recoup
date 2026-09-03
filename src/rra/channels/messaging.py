"""Messaging channel abstractions for SMS and WhatsApp delivery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from rra.domain.enums import ChannelType
from rra.domain.models import Case


@dataclass
class DeliveryReceipt:
    """Receipt for a delivered message."""

    message_id: str
    channel: ChannelType
    recipient_phone: str
    delivered: bool
    timestamp: datetime


class MessagingChannelClient:
    """Mock/Production messaging client for SMS & WhatsApp notification delivery."""

    def send_message(
        self,
        case: Case,
        channel: ChannelType,
        message_text: str,
    ) -> DeliveryReceipt:
        """Send a message to the customer phone number via SMS or WhatsApp."""
        phone = case.phone_number or "+919876543210"
        msg_id = f"msg_{hash(case.case_id + message_text) & 0xFFFFFFFF:08x}"

        return DeliveryReceipt(
            message_id=msg_id,
            channel=channel,
            recipient_phone=phone,
            delivered=True,
            timestamp=datetime.now(timezone.utc),
        )
