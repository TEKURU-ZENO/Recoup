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

Evaluated across a realistic 28-day subscription billing cycle where payment failure dates are distributed throughout the month. By sharing identical pseudorandom draws per case across arms (Common Random Numbers), the paired difference eliminates shared portfolio variance, yielding tight confidence intervals:

| Comparison | Isolated Variable | Paired Value Δ (INR) | Paired Case Δ (Count) | Core Empirical Mechanism |
|---|---|---|---|---|
| **NaiveUnbounded → NaiveBounded** | Bounded Guards & Links | **+1.65pp ± 1.51pp** | **+1.07pp ± 0.96pp** | **Channel substitution**: Eliminates futile retries on dead cards; routes to digital links |
| **NaiveBounded → SmartBounded** | Decoupled Dunning Ladder | **+2.37pp ± 1.13pp** | **+2.91pp ± 0.89pp** | **Decoupled dunning**: Day-1 nudge captures intent, 28th auto-debit captures liquidity (-71 retries) |
| **SmartBounded → SmartBoundedVoice** | LiveKit Voice Intercept (>₹5k) | **+3.91pp ± 2.05pp** | **+0.88pp ± 0.42pp** | **Targeted voice intervention**: 5.8 calls yield ₹16,632 net capital (37.4% conv., target >₹5k) |

---

## Key Analytical Findings

### 1. The Real Source of Lift: Channel Substitution, Not Retry Timing
Disaggregating the lift between unbounded and bounded execution reveals that the gain comes from **channel substitution on structural errors**:
- **`card_expired`**: **+10.4pp ± 4.9pp lift (Statistically established)**. Unbounded executes 3 futile backend retries ($P=0.00$), wasting retries on dead cards. Bounded guards prohibit retries and immediately dispatch a `method_switch_link` (926 links delivered across 20 seeds).
- **`3ds_dropoff`**: **+2.1pp ± 5.8pp lift (Directional, straddles zero)**. Bounded routes directly to `friction_reduction_link` (667 links delivered), though the wide confidence interval means it is not statistically established.
- **The constraints were the optimization**: Doing strictly less futile work forced the agent into higher-converting digital channels.

### 2. Breaking the Scheduling Null: The Decoupled Dunning Ladder
Why did traditional payday deferrals produce a null?
- **The Coupling Flaw**: Standard recovery ladders couple customer contact to backend auto-debits sequentially. Deferring the auto-debit to wait for payday delayed customer communications by 12–18 days, allowing fresh customer intent to decay exponentially ($\exp(-\lambda \times \Delta t)$ losing 45–60%).
- **The Decoupled Architecture**: When `INSUFFICIENT_FUNDS` occurs mid-month, the agent *decouples* customer communication velocity from auto-debit clearing schedules:
  - **Day 1 ($t=0$)**: Immediately dispatches a digital nudge with hosted payment link, capturing fresh intent while the customer is engaged.
  - **Day 28 (Payday)**: Defers backend auto-debit retries to the upcoming salary clearing window when bank balances credit.
- **The Result**: Converts customers via link if they can pay immediately, while preserving automated clearing for when liquidity peaks. This yields a statistically significant **+2.37pp ± 1.13pp Value Lift** and **+2.91pp ± 0.89pp Case Resolution Lift**, while **eliminating 71.3 futile retries per batch**.

### 3. Complementary Funnel Dynamics: Long Tail vs. Top of Book
The case delta and value delta point in distinct, complementary directions:
- **Decoupled Dunning (`NaiveBounded → SmartBounded`)**: **+2.91pp Cases vs +2.37pp Value**. The Day-1 digital nudge converts proportionally more small-to-median accounts (~₹1,200) whose intent is fresh and who can pay via UPI link immediately upon receipt.
- **Voice Telephony (`SmartBounded → SmartBoundedVoice`)**: **+0.88pp Cases vs +3.91pp Value**. Voice acts exclusively on stalled accounts at the top of the book (>₹5,000, averaging ₹9,185 per recovered case).
- **Synergy**: Decoupling drives volume at the long tail; voice drives value at the top. The two mechanisms are complementary, not redundant.

### 4. Voice Arm: Absolute Economics, Selection Effect & Sensitivity
- **Selection Effect & Variance**: Value Recovery Rate (+3.91pp) is driven by deliberate account targeting as much as conversion. Restricting voice to accounts $\ge$ ₹5,000 (averaging ₹9,185 per recovered case) produces a wider confidence interval on net recovery (₹16,632 ± ₹9,212) due to the heavy-tailed Pareto distribution across small-n batches (5.8 calls).
- **Absolute Economics**: Across 20 seeds, 5.8 calls placed cost **₹29.00** in SIP telephony and recover **₹16,631.92 ± ₹9,212.37 in net capital**.
- **Conversion Sensitivity & Break-Even**:
  - **At 37.4% conversion (baseline)**: ₹29.00 telephony spend recovers ₹16,632 net.
  - **At 15.0% conversion (stress test)**: Recovers ~₹6,200 net capital.
  - **Break-Even Conversion Rate**: Because each recovery captures ~₹9,185 against a ₹5.00 SIP call cost, the economic break-even is **0.055%** (1 successful conversion per 1,800 calls placed).

---

## Unit Economics & Cost Accounting (Per Batch Mean ± 95% CI)

| Economic Metric | NaiveUnbounded | NaiveBounded | SmartBounded | SmartBoundedVoice |
|---|---|---|---|---|
| **Gross Revenue Recovered** | ₹171,953 ± ₹13,961 | ₹179,408 ± ₹16,720 | ₹189,384 ± ₹16,362 | **₹206,651 ± ₹21,081** |
| Gateway MDR (2.0%) | ₹3,439 ± ₹279 | ₹3,588 ± ₹334 | ₹3,788 ± ₹327 | ₹4,133 ± ₹422 |
| Channel Delivery Spend (SMS/WA/Voice) | ₹70.54 ± ₹1.59 | ₹33.15 ± ₹1.49 | ₹34.74 ± ₹1.29 | ₹63.74 ± ₹5.88 |
| Contact Churn Fatigue Cost (₹45/excess contact) | ₹1,863.00 ± ₹195.23 | ₹0.00 | ₹0.00 | ₹261.00 ± ₹54.49 |
| **Net Recovered Capital** | ₹166,580 ± ₹13,783 | ₹175,787 ± ₹16,386 | ₹185,561 ± ₹16,035 | **₹202,193 ± ₹20,625** |
| **Incremental Net Capital vs Bounded** | -₹9,207 ± ₹3,618 | ₹0.00 (Baseline) | **+₹9,775 ± ₹1,340** | **+₹26,407 ± ₹5,120** |
| **Return on Incremental Channel Spend** | Negative | Baseline | **6,147.5x incremental** | **573.5x incremental** |
| Wasted Spend on Dead Accounts | ₹8.12 ± ₹0.69 | ₹0.00 | ₹0.00 | **₹0.00** |

*Cost Model*: Gateway retry fee = ₹0.00 (failed attempts not billed by Razorpay); Gateway MDR = 2.0% on successful recovery; SMS = ₹0.25; WhatsApp = ₹0.50; Voice call = ₹5.00; Churn fatigue = 1.5% hazard × ₹3,000 LTV on contacts >2 or on DND.

---

## Production Rollout Plan & Concrete Falsification Criteria

### Staged Production Deployment
1. **Phase 1: Passive Shadow Evaluation (Current)**: Ingest 100% of live merchant `payment.failed` webhooks without write actions. Validates taxonomy parsing coverage ($\ge 98\%$) and TRAI legality ($100\%$).
2. **Phase 2: 5% Canary Pilot (Channel Substitution Only)**: Route only structural failures (`card_expired`) to instant `method_switch_link` via WhatsApp. Zero automated backend retries attempted.
3. **Phase 3: Randomized Cohort Experiment (20% Ramp)**: Deploy decoupled dunning on `INSUFFICIENT_FUNDS` randomized by `subscription_id` hash against legacy 24/48/72h retries.

### Concrete Falsification Criteria (When to Reject the Architecture)
A production payments team must define what real-world observation would invalidate the system:
1. **Contact Fatigue Cliff**: If Day-1 digital nudges trigger customer opt-out or DND registration exceeding **2.5%** of contacted accounts (indicating premature contact creates annoyance rather than resolution).
2. **Absence of Payday Cyclicality**: If Day-28 salary auto-debit recovery does not exceed mid-month retries by at least **1.4x** (indicating customer liquidity is non-cyclical in that merchant's specific demographic).
3. **Net Margin Compression**: If net recovered capital does not exceed the naive 24/48/72h control by at least **+1.0pp** after deducting production WhatsApp utility fees (₹0.75/delivered message) and carrier DLT registration fees.

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
