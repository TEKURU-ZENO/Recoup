# AI Revenue Recovery Agent for Recurring Payments

Deterministic state engine, fenced LLM narrator, and 4-arm empirical benchmark comparison for recurring subscription recovery (Razorpay stack).

> *Simulated outcomes under stated assumptions. Simulator, seeds, and assumption sources are in the repo; `make bench` reproduces every figure below.*

> **Calibration notice**: Absolute recovery levels (≈52–57%) are uncalibrated against production cohorts (where industry dunning rates on failed recurring payments typically run 15–30%). The scientifically meaningful quantities are the *paired deltas between arms under identical Common Random Number (CRN) draws*, which cancel shared variance to isolate causal mechanisms.

---

## What the Agent Refused to Do

Out of 215 cases per batch, bounded execution **declined to chase 24.3 ± 2.0 cases** — mandate revocations, input-validation failures, and DND-registered accounts. Each declined chase is a case the agent examined, classified as structurally unrecoverable or consent-withdrawn, and refused to pursue.

The unbounded strawman arm chased all of them indiscriminately: **0.0 declined chases, 243.2 ± 8.4 guard violations** (TRAI contact hours, 48h cooling-off, and DND violations on outbound SMS).

---

## 4-Arm Paired-Delta Benchmark (20 Seeds × 215 Cases, CRN-Paired)

By sharing identical pseudorandom draws per case across arms (Common Random Numbers), the paired difference eliminates shared portfolio variance, yielding tight confidence intervals:

| Comparison | Isolated Variable | Paired Value Δ (INR) | Paired Case Δ (Count) | Core Empirical Mechanism |
|---|---|---|---|---|
| **NaiveUnbounded → NaiveBounded** | Bounded Guards & Links | **+1.70pp ± 1.48pp** | **+1.26pp ± 1.02pp** | **Channel substitution**: Eliminates futile retries on dead cards; routes to digital links |
| **NaiveBounded → SmartBounded** | Contextual Timing Schedule | **-0.07pp ± 0.54pp** | **+0.09pp ± 0.23pp** | **Liquidity vs attrition trade-off**: Fast retry avoids attrition cliff |
| **SmartBounded → SmartBoundedVoice** | LiveKit Voice Intercept (>₹5k) | **+3.53pp ± 1.85pp** | **+0.79pp ± 0.37pp** | **Targeted voice intervention**: 1.70 accounts recovered from 4.55 calls (37.4% conv.) |

> **Note on earlier +5.24pp figure**: Earlier preliminary drafts reported a single +5.24pp gross recovery lift that conflated compliance guardrails with voice intervention. The 4-arm design decomposes that figure into its two constituent drivers: **+1.70pp from compliance & channel substitution** and **+3.53pp from targeted voice intercepts**.

---

## Key Analytical Findings

### 1. The Real Source of Lift: Channel Substitution, Not Retry Timing
Disaggregating the lift between unbounded and bounded execution reveals that the gain comes from **channel substitution on structural errors**:
- **`card_expired`**: **+10.46pp ± 4.99pp lift (Statistically established)**. Unbounded executes 3 futile backend retries ($P=0.00$), wasting retries on dead cards. Bounded guards prohibit retries and immediately dispatch a `method_switch_link` (926 links delivered across 20 seeds).
- **`3ds_dropoff`**: **+4.93pp ± 7.02pp lift (Directional, but straddles zero)**. Bounded routes directly to `friction_reduction_link` (667 links delivered), though the wide confidence interval means it is not statistically established.
- **The constraints were the optimization**: Doing strictly less futile work forced the agent into higher-converting digital channels.

### 2. The Deferral Dilemma: Attrition Decay vs. Horizon Truncation
Why did deferring `insufficient_funds` to the 28th produce a null (-0.07pp ± 0.54pp)?
- **Diagnostic on the original batch clamp**: In the standard benchmark, portfolio creation is concentrated in the first 48 hours (April 1–2). Because these cases fail during the month-open salary window (1st–5th), the scheduler never triggered an 18-day deferral — it scheduled 24h retries for all settings $d \ge 1$.
- **Empirical sweep across a full 28-day billing cycle**: When cases are distributed across all billing dates (Day 1 to 28), two distinct regimes emerge:
  - **From 0d to 7d deferral (Constant Retries ≈ 340)**: Executed retries remain constant, but recovery steadily declines from **43.63% (Instant) → 43.09% (1d) → 41.67% (3d) → 40.52% (7d)**. This is pure **customer attrition decay**: holding retries stalls the escalation ladder, delaying digital nudges and allowing customer intent to decay.
  - **Past 7d deferral (14d to 21d, Retries drop to 222)**: **Horizon truncation** takes over. Cases failing late in the month (e.g. Day 22) that defer 14+ days cross the 30-day cutoff before retrying, dropping recovery to **34.87%**.
- **Conclusion**: Waiting for payday is penalized in both regimes — early in the month by attrition decay, and late in the month by horizon truncation. The optimal scheduler executes fast retries at instrument-optimal morning hours, reserving salary alignment only for payments failing within 2 days of payday (26th–27th IST).

### 3. Voice Arm: Arithmetic Transparency, Selection Effect & Sensitivity
- **Selection Effect**: Value Recovery Rate (+3.53pp) is driven by deliberate account targeting as much as conversion. Voice intercepts are restricted exclusively to stalled accounts with balances $\ge$ ₹5,000. While the portfolio median balance is ~₹1,200, the voice target accounts average **₹9,185 per recovered case**.
- **Exact Call Conversion Rate**: Across 20 seeds, the agent placed **4.55 ± 1.2 calls per batch**, yielding **1.70 ± 0.9 direct recoveries** — an exact **37.4% call conversion rate** (34 successes / 91 total calls placed).
- **Dual Metric Representation**:
  - **Case Resolution Lift**: **+0.79pp ± 0.37pp** (1.70 accounts / 215 batch).
  - **Value Recovery Lift**: **+3.53pp ± 1.85pp** (₹15,614.71 gross revenue / batch).
- **Conversion Sensitivity & Break-Even**:
  - **At 37.4% conversion (baseline)**: Incurs ₹22.50 in telephony costs, recovers ₹15,615 gross (₹15,075 net) $\to$ **686x telephony ROI**.
  - **At 15.0% conversion (stress test)**: Recovers 0.68 accounts (₹6,269 gross, ₹6,121 net) $\to$ **41.3x telephony ROI**.
  - **Break-Even Conversion Rate**: Because each recovery captures ~₹9,185 against a ₹5.00 SIP call cost, the economic break-even is **0.055%** (1 successful conversion per 1,800 calls placed).

---

## Unit Economics & Cost Accounting (Per Batch Mean ± 95% CI)

| Economic Metric | NaiveUnbounded | NaiveBounded | SmartBounded | SmartBoundedVoice |
|---|---|---|---|---|
| **Gross Revenue Recovered** | ₹218,740 ± ₹14,525 | ₹226,539 ± ₹17,705 | ₹226,281 ± ₹18,080 | **₹241,895 ± ₹21,492** |
| Gateway MDR (2.0%) | ₹4,375 ± ₹290 | ₹4,531 ± ₹354 | ₹4,526 ± ₹362 | ₹4,838 ± ₹430 |
| Channel Delivery Spend (SMS/WA/Voice) | ₹57.24 ± ₹1.31 | ₹21.80 ± ₹0.94 | ₹21.68 ± ₹0.92 | ₹44.42 ± ₹6.25 |
| Contact Churn Fatigue Cost (₹45/excess contact) | ₹1,518.75 ± ₹181.80 | ₹0.00 | ₹0.00 | ₹204.75 ± ₹54.44 |
| **Net Recovered Capital** | ₹212,789 ± ₹14,329 | ₹221,986 ± ₹17,352 | ₹221,733 ± ₹17,719 | **₹236,808 ± ₹21,041** |
| **Net ROI Multiple** | 35.70x | 48.75x | 48.75x | **46.58x** |
| Wasted Spend on Dead Accounts | ₹8.12 ± ₹0.69 | ₹0.00 | ₹0.00 | **₹0.00** |

*Cost Model*: Gateway retry fee = ₹0.00 (failed attempts not billed by Razorpay); Gateway MDR = 2.0% on successful recovery; SMS = ₹0.25; WhatsApp = ₹0.50; Voice call = ₹5.00; Churn fatigue = 1.5% hazard × ₹3,000 LTV on contacts >2 or on DND.

---

## Schema Conformance & Policy Legality Check (Shadow Mode)

Evaluated against a cohort of **400 synthetic-realistic merchant webhook transactions** (`payment.failed`) generated from real-world Razorpay error code schemas and distributions:
- **Taxonomy Coverage**: **99.0%** (396/400 mapped into actionable failure codes).
- **Policy Legality**: **100.0%** (zero proposed actions violated TRAI contact hours, cooling-off, or DND).
- **Declined Chases Refused**: **30 cases (7.5%)** correctly halted at Level 0.
- **Unmapped Gateway Anomalies**: Flagged `suspected_fraud_velocity_limit` for engineering review.

> *Data Provenance & Scope*: The 400 events are synthetic-realistic records matching real-world gateway error structures, not proprietary merchant data. Shadow mode verifies taxonomy parsing coverage and policy legality without side effects; causal revenue lift is established through CRN simulation. See [Shadow Mode Guide](docs/shadow-mode-guide.md).

---

## Ungrounded-Fact Rate: 0.0%

The fenced narrator client (`src/rra/narrator/client.py`) validates all LLM-generated customer communications against the strict grounding validator:
- Rejects fabricated rupee amounts not present in the case record.
- Rejects prohibited policy terms (unauthorized discounts, fee waivers, threats, cancellations).
- Replaces ungrounded responses with deterministic templates.
- **Ungrounded-fact rate: 0.0%** across all simulation runs and unit tests.

---

## Architectural Invariants

1. **Strict Layering**: `engine/` never imports `sim/` or `narrator/`. `sim/` never imports `engine/`. Enforced AST-level by `tests/test_layering.py`.
2. **Honesty Firewall**: The scheduler's beliefs (`engine/scheduler.py`) and the simulator's truth (`sim/outcome_model.py`) are deliberately separate and unequal.
3. **Common Random Numbers (CRN)**: Draws keyed on `(seed, case_id, action_type, ordinal)` — arms experience identical draws for identical action types.
4. **Integer Paise Money**: All financial arithmetic in integer paise (1 INR = 100 paise). Zero floating-point rounding drift.

---

## Verification Commands

```bash
# Full test suite (132 passing tests)
make test

# Reproduce 4-arm benchmark report over 20 seeds
make bench

# Run shadow-mode evaluation on 400 merchant transactions
make shadow

# Run interactive CLI walkthrough demo
make demo
```

---

## Documentation Links

- [Architecture Guide](docs/architecture.md)
- [Stated Model Assumptions](docs/assumptions.md)
- [Generated Benchmark Report](docs/benchmark-report.md)
- [Shadow Mode Integration Guide](docs/shadow-mode-guide.md)
