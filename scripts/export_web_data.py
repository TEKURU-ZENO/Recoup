"""Export generated benchmark + shadow-run data into JSON fixtures for the web dashboard.

The dashboard must never carry hand-typed statistics. This script is the single
bridge: it reads the *generated* artifacts

  - docs/benchmark-report.md   (produced by `make bench`, never hand-edited)
  - docs/shadow-decisions.jsonl (the committed 400-event shadow run)

and writes structured JSON into web/app/data/ which the Next.js app imports at
build time. Wired into `make bench` so the two can never drift.

Usage:
    python scripts/export_web_data.py            # parse existing generated artifacts
    python scripts/export_web_data.py --fresh    # regenerate benchmark-report.md first
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

DOCS = _REPO_ROOT / "docs"
REPORT_MD = DOCS / "benchmark-report.md"
SHADOW_JSONL = DOCS / "shadow-decisions.jsonl"
OUT_DIR = _REPO_ROOT / "web" / "app" / "data"

ARMS = ["NaiveUnbounded", "NaiveBounded", "SmartBounded", "SmartBoundedVoice"]

# mean ± ci, tolerating ₹ , thousands separators, +, pp / % / x suffixes
_NUM = r"[-+]?[\d,]+(?:\.\d+)?"
_MEAN_CI = re.compile(
    rf"(?P<mean>{_NUM})\s*(?:pp|%|x)?\s*(?:±|\+/-)\s*(?:₹)?\s*(?P<ci>{_NUM})"
)


def _f(s: str) -> float:
    return float(s.replace(",", "").replace("₹", "").replace("+", "").strip())


def _parse_mean_ci(cell: str) -> dict | None:
    m = _MEAN_CI.search(cell)
    if not m:
        return None
    mean, ci = _f(m.group("mean")), _f(m.group("ci"))
    return {
        "mean": mean,
        "ci": ci,
        "low": round(mean - ci, 4),
        "high": round(mean + ci, 4),
        "clears_zero": (mean - ci) * (mean + ci) > 0,
        "text": cell.strip(),
    }


def _tables(md: str) -> list[dict]:
    """Return every markdown table in the doc, keyed by the section heading above it."""
    out: list[dict] = []
    heading = ""
    rows: list[list[str]] = []
    for line in md.splitlines():
        h = re.match(r"^#{1,6}\s+(.*)", line)
        if h:
            heading = h.group(1).strip()
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue  # divider row
            rows.append(cells)
        else:
            if rows:
                out.append({"heading": heading, "rows": rows})
                rows = []
    if rows:
        out.append({"heading": heading, "rows": rows})
    return out


def _find(tables: list[dict], needle: str) -> list[list[str]]:
    for t in tables:
        if needle.lower() in t["heading"].lower():
            return t["rows"]
    return []


def parse_report(md: str) -> dict:
    tables = _tables(md)

    # header line: "> Benchmark run over 20 seeds (215 cases/seed, 30-day horizon, ...)"
    seeds = re.search(r"run over (\d+) seeds", md)
    cases = re.search(r"\((\d+) cases/seed", md)

    # --- Paired-delta summary --------------------------------------------------
    paired: list[dict] = []
    for row in _find(tables, "Paired-Delta Summary")[1:]:
        if len(row) < 4:
            continue
        comparison, metric, delta, interp = row[0], row[1], row[2], row[3]
        parsed = _parse_mean_ci(delta)
        paired.append(
            {
                "comparison": comparison,
                "metric": metric,
                "unit": "pp" if "pp" in delta else ("inr" if "₹" in delta else "count"),
                "delta": delta,
                "interpretation": interp,
                **(parsed or {"text": delta}),
            }
        )

    # --- Unit economics (arm columns) ---------------------------------------
    economics: list[dict] = []
    for row in _find(tables, "Unit Economics")[1:]:
        if len(row) < 5:
            continue
        if "return on incremental" in row[0].lower():
            continue  # vanity ratio — never surfaced on the dashboard
        economics.append(
            {
                "metric": row[0],
                "arms": {
                    arm: (_parse_mean_ci(row[i + 1]) or {"text": row[i + 1]})
                    for i, arm in enumerate(ARMS)
                },
            }
        )

    # --- Per-arm technical summary ----------------------------------------
    technical: list[dict] = []
    for row in _find(tables, "Per-Arm Technical Summary")[1:]:
        if len(row) < 5:
            continue
        technical.append(
            {
                "metric": row[0],
                "arms": {
                    arm: (_parse_mean_ci(row[i + 1]) or {"text": row[i + 1]})
                    for i, arm in enumerate(ARMS)
                },
            }
        )

    # --- Failure-mode disaggregation -------------------------------------
    failure_modes: list[dict] = []
    for row in _find(tables, "Failure-Mode Recovery Disaggregation")[1:]:
        if len(row) < 7:
            continue
        fc = row[0].strip("`")
        rates = {}
        for i, arm in enumerate(ARMS):
            m = re.search(r"([-+]?\d+(?:\.\d+)?)\s*%", row[i + 2])
            rates[arm] = float(m.group(1)) if m else None
        lift = _parse_mean_ci(row[6])  # driver text often carries "+10.4pp ± 4.9pp"
        failure_modes.append(
            {
                "failure_code": fc,
                "batch_total": int(re.sub(r"\D", "", row[1]) or 0),
                "rates": rates,
                "mechanism": row[6],
                "lift": lift,
            }
        )

    return {
        "generated_from": "docs/benchmark-report.md",
        "seeds": int(seeds.group(1)) if seeds else None,
        "cases_per_seed": int(cases.group(1)) if cases else None,
        "provenance": (
            f"{int(seeds.group(1)) if seeds else '?'} seeds x "
            f"{int(cases.group(1)) if cases else '?'} cases/seed, CRN-paired - `make bench` reproduces every figure"
        ),
        "paired_deltas": paired,
        "economics": economics,
        "technical": technical,
        "failure_modes": failure_modes,
    }


def parse_shadow(text: str) -> dict:
    events = [json.loads(line) for line in text.splitlines() if line.strip()]
    refused = [e for e in events if e.get("is_declined_chase")]
    by_code: dict[str, int] = {}
    for e in refused:
        by_code[e.get("failure_code") or "unmapped"] = by_code.get(e.get("failure_code") or "unmapped", 0) + 1
    mapped = sum(1 for e in events if e.get("is_mapped"))
    legal = sum(1 for e in events if e.get("is_legally_compliant"))
    return {
        "generated_from": "docs/shadow-decisions.jsonl",
        "total_events": len(events),
        "mapped_events": mapped,
        "taxonomy_coverage_pct": round(mapped / len(events) * 100, 1) if events else 0,
        "legal_compliance_pct": round(legal / len(events) * 100, 1) if events else 0,
        "refused_count": len(refused),
        "refused_pct": round(len(refused) / len(events) * 100, 1) if events else 0,
        "refused_by_code": by_code,
        "refused": refused,
        "events": events,
    }


def build_cases() -> tuple[list[dict], dict[str, list[dict]]]:
    """Run the offline deterministic engine over a small fixed portfolio.

    No API, no Razorpay credentials. Produces real FSM decisions and a real
    hash-chained audit trail per case. Identities are synthetic initials — the
    engine never needs a real name.
    """
    from datetime import datetime, timedelta, timezone

    from rra.audit.ledger import Ledger
    from rra.domain.enums import CaseStatus, FailureCode
    from rra.domain.models import Action, Case, Outcome
    from rra.engine.policy import next_action

    portfolio = [
        ("case_001", "sub_9f2a71c4", "A. Sharma", 249900, FailureCode.INSUFFICIENT_FUNDS, "+919876500011", False),
        ("case_002", "sub_3b8e40d9", "D. Patel", 650000, FailureCode.CARD_EXPIRED, "+919876500022", False),
        ("case_003", "sub_c14d92f7", "R. Kumar", 120000, FailureCode.MANDATE_REVOKED, None, False),
        ("case_004", "sub_7a5f1e30", "M. Iyer", 899000, FailureCode.THREE_DS_DROPOFF, "+919876500044", False),
        ("case_005", "sub_e2c6b038", "S. Nair", 45000, FailureCode.BANK_DOWNTIME, "+919876500055", True),
        ("case_006", "sub_16bd7a52", "K. Reddy", 310000, FailureCode.PAYMENT_TIMED_OUT, "+919876500066", False),
    ]
    now0 = datetime(2026, 4, 1, 9, 30, tzinfo=timezone.utc)

    cases_out: list[dict] = []
    audits_out: dict[str, list[dict]] = {}

    for cid, sub, name, amount, fc, phone, dnd in portfolio:
        case = Case(
            case_id=cid, subscription_id=sub, customer_name=name,
            amount_due_paise=amount, failure_code=fc, phone_number=phone, is_dnd=dnd,
        )
        ledger = Ledger()
        ledger.append(
            subscription_id=sub, actor="RAZORPAY_WEBHOOK_HANDLER",
            rule_triggered="EVENT_PAYMENT_FAILED",
            inputs={"event": "payment.failed", "reason": fc.value},
            execution_payload={"failure_code": fc.value},
        )
        history: list[tuple[Action, Outcome]] = []
        now = now0
        for _ in range(4):
            act = next_action(case, history, now, use_smart_scheduling=True, voice_enabled=True)
            if act is None:
                ledger.append(
                    subscription_id=sub, actor="AGENT_POLICY_ENGINE",
                    rule_triggered="HALT_NO_FURTHER_ACTION",
                    inputs={"escalation_level": case.escalation_level.value},
                    execution_payload={"status": case.status.value},
                )
                break
            ledger.append(
                subscription_id=sub, actor="AGENT_POLICY_ENGINE",
                rule_triggered=act.rule_id or act.action_type.value.upper(),
                inputs={"escalation_level": case.escalation_level.value, "attempt": case.attempt_count},
                execution_payload={
                    "action_type": act.action_type.value,
                    "channel": act.channel.value if act.channel else None,
                    "scheduled_at": act.scheduled_at.isoformat(),
                },
            )
            executed = act.model_copy(update={"executed_at": act.scheduled_at, "result": "dispatched"})
            history.append((executed, Outcome(
                case_id=case.case_id, action_id=act.action_id, success=False,
                amount_recovered_paise=0, timestamp=act.scheduled_at,
            )))
            case.attempt_count += 1
            now = act.scheduled_at + timedelta(hours=1)

        ledger.verify_chain()
        cases_out.append({
            **case.model_dump(mode="json"),
            "audit_record_count": len(ledger.records),
        })
        audits_out[cid] = [r.model_dump(mode="json") for r in ledger.records]

    return cases_out, audits_out


def main() -> None:
    if "--fresh" in sys.argv:
        print("Regenerating docs/benchmark-report.md ...")
        from rra.bench.report import main as bench_main

        bench_main()

    if not REPORT_MD.exists():
        sys.exit(f"missing {REPORT_MD} - run `make bench` first")
    if not SHADOW_JSONL.exists():
        sys.exit(f"missing {SHADOW_JSONL} - run `make shadow` first")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    benchmark = parse_report(REPORT_MD.read_text(encoding="utf-8"))
    shadow = parse_shadow(SHADOW_JSONL.read_text(encoding="utf-8"))

    (OUT_DIR / "benchmark.json").write_text(
        json.dumps(benchmark, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUT_DIR / "shadow-decisions.json").write_text(
        json.dumps(shadow, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    cases, audits = build_cases()
    (OUT_DIR / "cases.json").write_text(
        json.dumps({"generated_from": "offline deterministic engine (scripts/export_web_data.py)", "cases": cases, "audits": audits}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"wrote {OUT_DIR / 'benchmark.json'}  ({len(benchmark['paired_deltas'])} paired deltas)")
    print(f"wrote {OUT_DIR / 'shadow-decisions.json'}  ({shadow['refused_count']} refused / {shadow['total_events']} events)")
    print(f"wrote {OUT_DIR / 'cases.json'}  ({len(cases)} cases)")


if __name__ == "__main__":
    main()
