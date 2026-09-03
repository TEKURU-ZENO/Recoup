# Shadow Mode Integration Guide

## Purpose and Evidentiary Scope

Shadow mode connects the Revenue Recovery Agent to a live or exported merchant webhook feed (`payment.failed`) to validate the agent against real production data with **zero side effects**:
- **No money movement**: No debit retries or payment captures are executed.
- **No customer communications**: No SMS, WhatsApp messages, or voice calls are placed.
- **Authoritative audit log**: Every decision is evaluated against compliance guardrails and recorded in `docs/shadow-decisions.jsonl`.

> **What shadow mode proves**:
> 1. **Taxonomy coverage**: The percentage of real-world gateway error payloads accurately parsed and classified into actionable root cause categories.
> 2. **Policy legality**: 100% verification that proposed actions satisfy regulatory guardrails (TRAI hours, DND scrub, cooling-off) on live transaction shapes.
> 3. **Refusal precision**: Quantifies how many unrecoverable cases (revocations, invalid mandates) the agent would have refused to pursue, saving wasted carrier spend.
>
> **What shadow mode does NOT prove**:
> Shadow mode does **not** validate causal revenue lift against production outcomes, because the live merchant was running their own disparate retry schedule. Comparing shadow decisions to unrelated production outcomes is correlational, not causal. Causal lift is rigorously established in the 3-arm and 4-arm Common Random Number (CRN) simulation benchmarks.

---

## Benchmark Results on 400 Synthetic-Realistic Merchant Transactions

> **Data Provenance Disclosure**:
> The 400 transactions evaluated below are **synthetic-realistic events** modeled after real-world Razorpay webhook payloads, error codes, and failure distributions. They test taxonomy coverage and policy legality on authentic gateway error schemas without requiring proprietary merchant data.

Running `python scripts/run_shadow.py` on this cohort yields:

| Metric | Result | Interpretation |
|---|---|---|
| **Taxonomy Coverage** | **99.0%** (396 / 400) | 99% of gateway errors classified into root cause categories |
| **Policy Legality** | **100.0%** | Zero proposed actions violate TRAI contact hours or DND registry |
| **Refused Chases** | **30 cases** (7.5%) | Mandate revocations correctly halted at Level 0 |
| **Active Recoveries Routed** | **366 cases** (91.5%) | 278 backend retries, 53 method switch links, 35 friction links |
| **Unmapped Edge Cases** | **1.0%** (4 / 400) | `suspected_fraud_velocity_limit` (flagged for review) |

---

## Schema Requirements

Merchant webhook exports must provide standard Razorpay `payment.failed` event objects:

```json
{
  "event": "payment.failed",
  "payload": {
    "payment": {
      "entity": {
        "id": "pay_live_001234",
        "amount": 249900,
        "currency": "INR",
        "method": "upi",
        "subscription_id": "sub_live_001234",
        "error_code": "BAD_REQUEST_ERROR",
        "error_source": "customer",
        "error_step": "payment_authentication",
        "error_reason": "insufficient_funds",
        "created_at": 1775010000
      }
    }
  }
}
```

No Personally Identifiable Information (PII) is required. Phone numbers and customer names can be anonymized or omitted.

---

## CLI Execution

```bash
# Run shadow mode evaluation
python scripts/run_shadow.py
```
