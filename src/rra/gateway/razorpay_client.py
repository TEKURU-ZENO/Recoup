"""Razorpay Gateway Client (Test Mode).

Provides async integration for managing subscriptions, charges, and payment links
in Razorpay test mode.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

RAZORPAY_API_BASE = "https://api.razorpay.com/v1"


class RazorpayGatewayClient:
    """Razorpay API client for subscription management and charge attempts."""

    def __init__(
        self,
        key_id: str | None = None,
        key_secret: str | None = None,
    ) -> None:
        self.key_id = key_id or os.getenv("RAZORPAY_KEY_ID", "rzp_test_mockkey123")
        self.key_secret = key_secret or os.getenv("RAZORPAY_KEY_SECRET", "mocksecret123")

    @property
    def _auth(self) -> tuple[str, str]:
        return (self.key_id, self.key_secret)

    async def create_plan(
        self,
        period: str = "monthly",
        interval: int = 1,
        name: str = "Standard Recurring Subscription",
        amount_paise: int = 249900,
        currency: str = "INR",
    ) -> dict[str, Any]:
        """Create a subscription plan."""
        payload = {
            "period": period,
            "interval": interval,
            "item": {
                "name": name,
                "amount": amount_paise,
                "currency": currency,
            },
        }
        # In mock / unit testing mode, return simulated payload if no live key
        if self.key_id.startswith("rzp_test_mock"):
            return {
                "id": "plan_mock123",
                "entity": "plan",
                "interval": interval,
                "period": period,
                "item": payload["item"],
            }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{RAZORPAY_API_BASE}/plans",
                auth=self._auth,
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def create_subscription(
        self,
        plan_id: str,
        total_count: int = 12,
        customer_notify: int = 1,
    ) -> dict[str, Any]:
        """Create a customer recurring subscription."""
        payload = {
            "plan_id": plan_id,
            "total_count": total_count,
            "customer_notify": customer_notify,
        }
        if self.key_id.startswith("rzp_test_mock"):
            return {
                "id": "sub_mock123",
                "entity": "subscription",
                "plan_id": plan_id,
                "status": "authenticated",
            }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{RAZORPAY_API_BASE}/subscriptions",
                auth=self._auth,
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def create_payment_link(
        self,
        subscription_id: str,
        amount_paise: int,
        description: str,
        customer_phone: str | None = None,
    ) -> str:
        """Generate a Razorpay instant payment switch / recovery link."""
        if self.key_id.startswith("rzp_test_mock"):
            return f"https://rzp.io/i/{subscription_id}"

        payload = {
            "amount": amount_paise,
            "currency": "INR",
            "accept_partial": False,
            "description": description,
            "reference_id": subscription_id,
        }
        if customer_phone:
            payload["customer"] = {"contact": customer_phone}

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{RAZORPAY_API_BASE}/payment_links",
                auth=self._auth,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("short_url", f"https://rzp.io/i/{subscription_id}")
