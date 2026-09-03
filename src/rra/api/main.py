"""FastAPI main application entrypoint."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from rra.audit.ledger import Ledger
from rra.bench.report import run_benchmark
from rra.gateway.webhooks import InvalidWebhookSignatureError, WebhookManager

app = FastAPI(
    title="Revenue Recovery Agent API",
    description="Deterministic policy engine & fenced LLM dunning framework.",
    version="0.1.0",
)

# Enable CORS for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared in-memory state for local server API
webhook_manager = WebhookManager()
cached_benchmark_results: dict[str, Any] = {}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "system": "Revenue Recovery Agent API"}


@app.post("/webhooks/razorpay")
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(default=""),
) -> dict[str, Any]:
    """Razorpay test mode webhook endpoint with HMAC-SHA256 verification."""
    raw_body = await request.body()
    try:
        event_payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON request body")

    try:
        result = webhook_manager.process_event(
            raw_body=raw_body,
            signature_header=x_razorpay_signature,
            event_payload=event_payload,
        )
        return result
    except InvalidWebhookSignatureError as err:
        raise HTTPException(status_code=400, detail=str(err))


@app.get("/cases")
def list_cases() -> list[dict[str, Any]]:
    """Return all active and historical cases."""
    return [c.model_dump() for c in webhook_manager.active_cases.values()]


@app.get("/cases/{case_id}")
def get_case_detail(case_id: str) -> dict[str, Any]:
    """Return single case details."""
    for c in webhook_manager.active_cases.values():
        if c.case_id == case_id or c.subscription_id == case_id:
            return c.model_dump()
    raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")


@app.get("/cases/{subscription_id}/audit")
def get_case_audit_trail(subscription_id: str) -> list[dict[str, Any]]:
    """Return hash-chained audit log records for a case."""
    records = webhook_manager.ledger.for_subscription(subscription_id)
    return [r.model_dump() for r in records]


@app.get("/benchmark")
def get_benchmark_report() -> dict[str, Any]:
    """Return benchmark metrics results."""
    global cached_benchmark_results
    if not cached_benchmark_results:
        results = run_benchmark(seeds=[1, 2, 3], n_cases=50)
        cached_benchmark_results = {
            arm: [m.to_dict() for m in metrics_list]
            for arm, metrics_list in results.items()
        }
    return cached_benchmark_results
