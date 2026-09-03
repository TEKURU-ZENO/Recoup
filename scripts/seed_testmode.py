"""Script to create real Razorpay test-mode subscriptions and simulate webhook events."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time

from rra.gateway.razorpay_client import RazorpayGatewayClient


async def main() -> None:
    print("Initializing Razorpay test-mode client...")
    client = RazorpayGatewayClient()

    # 1. Create plan
    plan = await client.create_plan(
        name="Pro Subscription Monthly",
        amount_paise=249900,
    )
    print(f"Created Plan: {plan['id']}")

    # 2. Create subscription
    sub = await client.create_subscription(plan_id=plan["id"])
    print(f"Created Subscription: {sub['id']}")

    # 3. Create recovery link
    link = await client.create_payment_link(
        subscription_id=sub["id"],
        amount_paise=249900,
        description="Subscription Payment Recovery Link",
    )
    print(f"Generated Recovery Link: {link}")

    # Build simulated webhook payload
    payload = {
        "entity": "event",
        "account_id": "acc_test123",
        "event": "payment.failed",
        "created_at": int(time.time()),
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test999",
                    "amount": 249900,
                    "currency": "INR",
                    "subscription_id": sub["id"],
                    "contact": "+919876543210",
                    "error": {
                        "code": "BAD_REQUEST_ERROR",
                        "source": "customer",
                        "step": "payment_authentication",
                        "reason": "insufficient_funds",
                        "description": "Payment failed due to insufficient funds",
                    },
                    "notes": {"customer_name": "Aarav Sharma"},
                }
            }
        },
    }

    raw_body = json.dumps(payload).encode("utf-8")
    secret = "mocksecret123"
    signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    print(f"\nSimulated Webhook Event 'payment.failed' generated.")
    print(f"Signature: {signature}")
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
