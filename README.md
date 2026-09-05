# Recoup — AI Revenue Recovery Agent for Recurring Payments

Deterministic state engine, fenced LLM narrator, and 4-arm empirical benchmark comparison for recurring subscription recovery (Razorpay stack).

> *Simulated outcomes under stated assumptions. Simulator, seeds, and assumption sources are in the repo; `make bench` reproduces every figure below.*

> **Calibration notice**: The simulator's absolute recovery levels — NaiveUnbounded ≈ 40.8% value / 41.2% cases, SmartBoundedVoice ≈ 48.8% / 46.1% — sit at the **optimistic end** of directional industry ranges (passive email ~15–25%, retries + branched dunning ~25–40%, omni-channel ~35–45%; see [`docs/assumptions.md`](docs/assumptions.md)). They are a property of the outcome model's base probabilities, **not** a validated match to a production cohort. The scientifically meaningful quantities are the *paired deltas between arms under identical Common Random Number (CRN) draws*, which cancel shared variance to isolate causal mechanisms. Production calibration is Phase 1 of the rollout plan below.

---

## Demo

- **▶ Walkthrough video:**(https://drive.google.com/file/d/1SFal8apQwOi6HjUnFGKxZ32HZTKn5bl9/view?usp=sharing)
- **Dashboard (local):** `cd web && npm install && npm run dev` → <http://localhost:3000> — narrative walk of the result, the mechanism, the refusal ledger, and a live signed-webhook trigger. Optionally run the API too (`uvicorn rra.api.main:app --reload`) for live case data.
- **CLI walkthrough:** `make demo` — end-to-end ingestion → taxonomy → audit chain → policy decision → shadow validation → benchmark sample.

---

## What the Agent Refused to Do

Out of 215 cases per batch, bounded execution **declined to chase 24.3 ± 2.0 cases** — mandate revocations, input-validation failures, and DND-registered accounts. Each declined chase is a case the agent examined, classified as structurally unrecoverable or consent-withdrawn, and refused to pursue.

The unbounded strawman arm chased all of them indiscriminately: **0.0 declined chases, 286.9 ± 8.2 guard violations** (TRAI contact hours, 48h cooling-off, and DND violations on outbound SMS) — every one a real regulatory breach the bounded arm never commits.

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

> The lift from bounded to smart execution has two sources. They are presented largest-first
> below — but the larger one (decoupled timing, **+2.37pp**) was found *after* a naive
> payday-deferral heuristic measured a flat null. The finding is that the null was a design
> flaw in the heuristic, not an absence of signal. Voice is a separate, top-of-book lever
> (findings 3 and 5).

### 1. The Largest Lever: Breaking the Scheduling Null with a Decoupled Dunning Ladder
Why did traditional payday deferrals produce a null?
- **The Coupling Flaw**: Standard recovery ladders couple customer contact to backend auto-debits sequentially. Deferring the auto-debit to wait for payday delayed customer communications by 12–18 days, allowing fresh customer intent to decay exponentially ($\exp(-\lambda \times \Delta t)$ losing 45–60%).
- **The Decoupled Architecture**: When `INSUFFICIENT_FUNDS` occurs mid-month, the agent *decouples* customer communication velocity from auto-debit clearing schedules:
  - **Day 1 ($t=0$)**: Immediately dispatches a digital nudge with hosted payment link, capturing fresh intent while the customer is engaged.
  - **Day 28 (Payday)**: Defers backend auto-debit retries to the upcoming salary clearing window when bank balances credit.
- **The Result**: Converts customers via link if they can pay immediately, while preserving automated clearing for when liquidity peaks. This yields a statistically significant **+2.37pp ± 1.13pp Value Lift** and **+2.91pp ± 0.89pp Case Resolution Lift**, while **eliminating 71.3 futile retries per batch**. This is the single largest paired delta in the benchmark.

### 2. The Second Lever: Channel Substitution on Structural Errors
Disaggregating the lift between unbounded and bounded execution shows a second, smaller effect (**+1.65pp ± 1.51pp** overall) driven by **channel substitution on structurally dead payment methods**:
- **`card_expired`**: **+10.4pp ± 4.9pp lift (statistically established)**. Unbounded executes 3 futile backend retries ($P=0.00$), wasting retries on dead cards. Bounded guards prohibit retries and immediately dispatch a `method_switch_link` (926 links delivered across 20 seeds).
- **`3ds_dropoff`**: **+2.1pp ± 5.8pp lift (directional only — CI straddles zero)**. Bounded routes directly to `friction_reduction_link` (667 links delivered); the wide interval means it is *not* statistically established, and the dashboard labels it as such.
- **The constraints were the optimization**: doing strictly less futile work forced the agent into higher-converting digital channels.

### 3. Complementary Funnel Dynamics: Long Tail vs. Top of Book
The case delta and value delta point in distinct, complementary directions:
- **Decoupled Dunning (`NaiveBounded → SmartBounded`)**: **+2.91pp Cases vs +2.37pp Value**. The Day-1 digital nudge converts proportionally more small-to-median accounts (~₹1,200) whose intent is fresh and who can pay via UPI link immediately upon receipt.
- **Voice Telephony (`SmartBounded → SmartBoundedVoice`)**: **+0.88pp Cases vs +3.91pp Value**. Voice acts exclusively on stalled accounts at the top of the book (>₹5,000, averaging ₹9,185 per recovered case).
- **Synergy**: Decoupling drives volume at the long tail; voice drives value at the top. The two mechanisms are complementary, not redundant.

### 4. What Would Invalidate This
The absolute recovery levels are optimistic (see the calibration notice at the top) — so the
project stakes its claim on the *paired deltas*, and states up front what real-world evidence
would reject each mechanism. See **Concrete Falsification Criteria** below: a contact-fatigue
cliff above 2.5% opt-out, absent payday cyclicality (< 1.4× payday vs mid-month), or net-margin
compression below +1.0pp after production messaging fees would each falsify the architecture.

### 5. Voice Arm: Absolute Economics, Selection Effect & Sensitivity
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
| **Incremental Net Capital vs Bounded** | -₹9,207 ± ₹6,210 | ₹0.00 (Baseline) | **+₹9,775 ± ₹4,754** | **+₹26,407 ± ₹11,060** |
| Incremental Channel Spend vs Bounded | +₹37.39 ± ₹1.76 | ₹0.00 (Baseline) | +₹1.59 ± ₹0.78 | +₹30.59 ± ₹6.22 |
| Wasted Spend on Dead Accounts | ₹8.12 ± ₹0.69 | ₹0.00 | ₹0.00 | **₹0.00** |

**The honest statement is the absolute pairing, not a ratio.** ₹1.59 more channel spend (SmartBounded) buys **+₹9,775 ± ₹4,754** net capital; ₹30.59 more including voice (SmartBoundedVoice) buys **+₹26,407 ± ₹11,060**. We do not publish a return multiple — a ratio on a ~₹1.59 denominator is a vanity number.

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
make test    # Full test suite — 133 passing tests (also runs in CI on every push)
make bench   # Reproduce the 4-arm benchmark report over 20 seeds, and refresh web/app/data/*.json
make shadow  # Shadow-mode evaluation over 400 synthetic-realistic merchant transactions
make demo    # Interactive CLI walkthrough
```

CI: [`.github/workflows/test.yml`](.github/workflows/test.yml) runs `make test` on every push and PR — the badge/check on the repo front page is the verifiable evidence that the suite passes.

---

## Codebase Map

### Deterministic engine — `src/rra/` (no LLM, no simulator imports)

| Module | Responsibility |
|---|---|
| `domain/enums.py`, `domain/models.py` | Pure types; `Case`/`Action`/`Outcome`/`AuditRecord` in integer paise |
| `engine/taxonomy.py` | Razorpay gateway error → `FailureCode` |
| `engine/fsm.py` | Escalation-level transition table |
| `engine/guards.py` | 9 regulatory / operational guardrails (TRAI hours, cooling-off, DND, …) |
| `engine/scheduler.py` | Salary-proximity + downtime hold-and-resume scheduling |
| `engine/policy.py` | Orchestrates taxonomy → FSM → guards → scheduler into one `next_action` |
| `audit/ledger.py` | Append-only SHA-256 hash-chained ledger with `verify_chain()` |
| `gateway/webhooks.py` | HMAC-SHA256 verification, idempotency, runs the policy engine on ingest |
| `gateway/razorpay_client.py` | Test-mode API client |
| `narrator/` (4 files) | Fenced LLM client + grounding validator + deterministic templates |
| `channels/messaging.py`, `channels/voice/` | SMS/WhatsApp sender; LiveKit voice worker, P2P tool, Hinglish prompt |
| `sim/` (5 files) | Sealed ground-truth oracle — clock, CRN RNG, downtime, outcome model, portfolio |
| `bench/` (arms, runner, metrics, report) | 4-arm CRN harness; `report.py` generates `docs/benchmark-report.md` |
| `api/main.py` | FastAPI: `/webhooks/razorpay`, `/cases`, `/cases/{id}/audit`, `/benchmark`, `/health` |

### Dashboard — `web/` (Next.js 14, App Router, vanilla CSS)

| Piece | Responsibility |
|---|---|
| `app/page.tsx` | **Result** — recovery lift + 95% CI, funnel, paired-delta interval plot |
| `app/benchmark/page.tsx` | **Why it works** — every delta drawn as a dot + whisker vs zero, unit economics |
| `app/refused/page.tsx` | **What we refused** — the 30 refused synthetic events, `0` vs `286.9` guard-violation bar |
| `app/cases/page.tsx` | **Portfolio** table + **live signed-webhook trigger** |
| `app/case/[id]/page.tsx`, `app/audit/[id]/page.tsx` | Case timeline; hash-chain ledger with client-side `verify_chain` |
| `app/api/simulate-webhook/route.ts` | Server-side HMAC-SHA256 signer → POSTs a real `payment.failed` to the API |
| `app/components/` | `IntervalPlot`, `Kpi`, `Shell` (nav + live/fixture indicator), `LiveWebhookPanel`, `primitives`, `icons` |
| `lib/` | `data.ts` (typed fixtures), `api.ts` (`fetchWithFallback`), `cases.ts`, `format.ts` |
| `app/data/*.json` | Generated by `scripts/export_web_data.py` — **no hand-typed statistics** |

### Scripts — `scripts/`

`export_web_data.py` (report + shadow run → `web/app/data/`), `run_demo.py`, `run_shadow.py`, `seed_testmode.py`.

---

## Documentation Links

- [Architecture Guide](docs/architecture.md)
- [Stated Model Assumptions](docs/assumptions.md)
- [Generated Benchmark Report](docs/benchmark-report.md)
- [Shadow Mode Integration Guide](docs/shadow-mode-guide.md)
