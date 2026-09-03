# Assumptions

Every constant used in the simulator's outcome model is documented here, tagged:

- `[sourced]` — a specific, checkable public fact (published tariffs, bank maintenance windows, regulatory schedules).
- `[estimate]` — a directional industry range from public write-ups; no single citable figure with a stable methodology. Not tuned to hit any particular value.
- `[judgment]` — the author's own estimate.

None of these are calibrated against a production cohort. The benchmark's claim is the **paired deltas between arms**, which cancel the absolute level.

> This file is a credibility asset — reviewers trust stated assumptions
> far more than unexplained precision.

> **Calibration notice**: The absolute recovery rates produced by this simulator
> (≈41–48% on the realistic 28-day billing cycle portfolio) are **uncalibrated against production data**.
> Industry dunning recovery on failed recurring payments typically runs in the 15–30% range.
> The base probabilities below are set to produce differentiated behavior across
> failure codes, not to match a specific production cohort.
>
> The meaningful quantities in the benchmark are the **paired deltas between arms
> under identical CRN draws**, which isolate the causal contribution of each
> design decision independent of the absolute level. See `docs/benchmark-report.md`.

---

## Industry Recovery Rates — Directional Context (NOT a calibration)

These are **directional ranges** gathered from public write-ups on failed-payment recovery.
They are `[estimate]`, not `[sourced]`: the underlying reports do not publish a single
citable figure with a stable methodology, and vendor blog numbers vary widely by segment
(B2B vs B2C, ticket size, channel mix). We do **not** tune the simulator to hit any of them.

| Approach | Rough published range | Notes |
|---|---|---|
| Passive email-only dunning | ~15–25% | Widely cited "baseline" band across dunning vendors (Baremetrics, Paddle write-ups). |
| Retries + branched dunning sequence | ~25–40% | Card-retry engines plus reason-branched messaging; Stripe's own headline "recover 55% on average" blends B2B and is not segment-adjusted, third-party B2C estimates land ~25–35%. |
| Omni-channel (SMS + WhatsApp + hosted links + voice) | ~35–45% | Best-case multi-channel setups; small number of public data points, high variance. |

**How our numbers sit against this:** the simulator's absolute recovery levels
(NaiveUnbounded ≈ 40.8% value / 41.2% cases; SmartBoundedVoice ≈ 48.8% / 46.1%) sit at the
**optimistic end** of these ranges. That is a property of the outcome model's base
probabilities, not a validated match to a production cohort. The claim this project makes is
the set of **paired deltas between arms under common random numbers** — those cancel the
absolute level. Production calibration is Phase 1 of the rollout plan (`docs/benchmark-report.md`).

The `NaiveUnbounded` arm is a **strawman** (fixed 24h/48h retries, untargeted messaging, no
guards); its ~40.8% is not a claim that untargeted dunning performs that well, it is the shared
starting point every arm is measured against.

---

## Salary Proximity Model

| Constant | Value | Source |
|---|---|---|
| Salary peak days | 30th, 31st, 1st, 2nd, 3rd, 4th, 5th | `[estimate]` — month-end/month-start payroll concentration in India; directional |
| Proximity kernel | Gaussian, σ = 3 days | `[judgment]` — spread of payroll batch clearing across banks |
| Simulator peak center | 30th–2nd | `[judgment]` — slightly earlier than engine's belief (1st–3rd) to maintain separation |
| Engine belief center | 1st–3rd | `[judgment]` — deliberately offset from simulator truth |

## Attrition Decay

| Constant | Value | Source |
|---|---|---|
| Decay constant (λ) | 0.05 / day | `[estimate]` — ~14-day billing-intent half-life; directional, from public churn write-ups |
| Half-life | ~13.9 days | Derived: ln(2) / 0.05 |
| Model | Exponential: exp(-λ × elapsed_days) | Standard churn hazard model |

## Base Retry Probabilities (Backend Retry)

| Failure Code | Base P(success) | Source |
|---|---|---|
| `insufficient_funds` | 0.25 × salary_proximity × attrition | `[estimate]` — peak auto-retry recovery; directional band ~20–35% across public card-retry write-ups, set at the low end |
| `bank_downtime` (during outage) | 0.02 | `[judgment]` — near-zero, small chance of partial recovery |
| `bank_downtime` (after recovery) | 0.70 × attrition | `[estimate]` — post-outage bounce-back; directional ~70–80% |
| `card_expired` | **0.00** | Structural: expired card cannot succeed on retry |
| `3ds_dropoff` | 0.03 | `[judgment]` — same 3DS challenge will likely fail again |
| `mandate_revoked` | **0.00** | Structural: consent withdrawn permanently |
| `payment_timed_out` | 0.55 × attrition | `[estimate]` — transient timeout reconnection; directional ~50–60% |
| `input_validation_failed` | **0.00** | Structural: system integration issue |

## Link / Nudge Conversion Rates

| Failure Code | Nudge P(success) | Channel | Source |
|---|---|---|---|
| `insufficient_funds` | 0.12 × attrition | SMS/WhatsApp reminder | `[estimate]` — self-serve link conversion; directional ~10–14% |
| `card_expired` | 0.18 × attrition | Method-switch link | `[estimate]` — card-update link conversion; directional ~18–22% |
| `card_expired` (SMS/WhatsApp) | 0.144 × attrition | Generic nudge (0.18 × 0.8) | `[judgment]` — 20% friction penalty without direct link |
| `3ds_dropoff` | 0.22 × attrition | Friction-reduction link | `[estimate]` — hosted-link completion; directional ~20–25% |
| `3ds_dropoff` (SMS/WhatsApp) | 0.154 × attrition | Generic nudge (0.22 × 0.7) | `[judgment]` — 30% friction penalty without direct link |
| `payment_timed_out` | 0.10 × attrition | Generic payment link | `[judgment]` |
| `bank_downtime` | 0.00 | N/A — only backend retries work | Structural |
| `mandate_revoked` | **0.00** | N/A — consent withdrawn | Structural |

## Voice Call P2P Capture Rates

| Failure Code | P(P2P captured) | P2P Kept Rate | Effective P(recovery) | Source |
|---|---|---|---|---|
| `insufficient_funds` | 0.55 | 0.68 | 0.374 | `[estimate]` — collections telephony; directional ~50–60% P2P, ~65–70% fulfillment |
| `card_expired` | 0.45 | 0.68 | 0.306 | `[estimate]` — collections telephony on payment-method update |
| `3ds_dropoff` | 0.40 | 0.68 | 0.272 | `[estimate]` — telephony assistance on 3DS drop-off completion |
| `mandate_revoked` | **0.00** | — | **0.00** | Structural |
| `bank_downtime` | 0.00 | — | 0.00 | N/A — infrastructure issue |
| `payment_timed_out` | 0.00 | — | 0.00 | N/A — transient, retry suffices |

> **P2P Kept Rate**: 68% of verbal promise-to-pay commitments result in actual payment.
> `[judgment]` — based on general collections industry benchmarks (60–75% range).

## Portfolio Generation Parameters

| Constant | Value | Source |
|---|---|---|
| Amount distribution | Log-normal: μ=7.09, σ=1.0 | `[judgment]` — median ~₹1,200 |
| Amount floor | ₹300 | `[judgment]` |
| Amount cap | ₹50,000 | `[judgment]` |
| Default batch size | 215 cases | Design choice |
| `insufficient_funds` share | 42% | `[estimate]` — largest single failure class in Indian recurring payments; directional |
| `bank_downtime` share | 21% | `[estimate]` — directional, from public gateway status write-ups |
| `card_expired` share | 14% | `[judgment]` |
| `3ds_dropoff` share | 11% | `[judgment]` |
| `mandate_revoked` share | 8% | `[judgment]` |
| `payment_timed_out` share | 4% | `[judgment]` |
| UPI Autopay share | 50% | `[estimate]` — reflects UPI AutoPay's dominant share of new recurring mandates; directional |
| Card Recurring share | 30% | `[judgment]` |
| e-Mandate share | 20% | `[judgment]` |
| DND prevalence | 15% | `[judgment]` |
| Phone presence | 92% | `[judgment]` |

## Bank Downtime Model

| Constant | Value | Source |
|---|---|---|
| Scheduled maintenance | 00:00–04:00 IST daily | `[sourced]` SBI/HDFC/ICICI published CBS windows |
| Unscheduled outages | 2–4 per month, 2–6 hours each | `[judgment]` |
| Outage hours range | 06:00–22:00 IST | `[judgment]` — avoids overlap with scheduled maintenance |

## Simulation Parameters

| Constant | Value | Source |
|---|---|---|
| Simulation horizon | 30 days | Design choice — allows salary-window deferrals to pay off |
| Retry cycle | 30 days (matches horizon) | Design choice |
| MAX_RETRIES per cycle | 3 backend retries | Design choice |
| Common random numbers | SHA-256 keyed on (seed, case_id, action_type, ordinal) | Design choice |

## Unit Economics & Cost Parameters

| Parameter | Value | Source |
|---|---|---|
| Gateway MDR fee | 2.0% (200 bps) of gross recovered value | `[sourced]` Standard Indian recurring payment gateway pricing |
| Gateway failed retry fee | ₹0.00 | `[sourced]` Razorpay fee structure (merchants are not billed for failed debits) |
| SMS Nudge cost | ₹0.25 | `[sourced]` Indian DLT bulk SMS tariff |
| WhatsApp template cost | ₹0.50 | `[sourced]` Meta WhatsApp Business API marketing template rate (India) |
| Voice call cost | ₹5.00 | `[judgment]` LiveKit + Twilio SIP trunk per-call compute and telephony charges |
| Hosted link generation | ₹0.00 | `[sourced]` Standard hosted checkout / mandate update links have zero marginal cost |
| Average customer LTV | ₹3,000 | `[judgment]` Mid-market Indian recurring subscription annual contract value |
| Churn hazard per excess contact | 1.5% | `[judgment]` Contact fatigue probability for contacts >2 or contacts to DND numbers |
| Expected churn cost per excess contact | ₹45.00 | Derived: 1.5% × ₹3,000 LTV |

## Liquidity vs Attrition Trade-off (Deferral Sweep)

| Finding | Value | Interpretation |
|---|---|---|
| Fast retry lift (0-day deferral) | +2.63pp ± 1.36pp | Immediate retries avoid customer attrition decay cliff |
| Payday deferral penalty (10-18 days) | ~45-60% probability loss | $\exp(-0.05 \times \Delta t)$ completely offsets liquidity gains |
| Optimal policy | Fast retry + capped deferral | Human intuition ("wait for payday") fails without active engagement |

