"""Tests for hash-chained tamper-evident audit ledger."""

import json
from pathlib import Path

import pytest

from rra.audit.ledger import Ledger, LedgerTamperError


class TestAuditLedger:
    """Tamper verification and hash-chain tests."""

    def test_chain_append_and_verify(self):
        ledger = Ledger()
        r1 = ledger.append(
            subscription_id="sub_100",
            actor="POLICY_ENGINE",
            rule_triggered="RULE_INIT",
            inputs={"error": "insufficient_funds"},
        )
        r2 = ledger.append(
            subscription_id="sub_100",
            actor="POLICY_ENGINE",
            rule_triggered="RULE_RETRY",
            inputs={"attempt": 1},
        )

        assert r1.previous_hash == "genesis"
        assert r2.previous_hash == r1.record_hash
        assert ledger.verify_chain() is True

    def test_jsonl_persistence_and_loading(self, tmp_path: Path):
        file_path = tmp_path / "audit.jsonl"
        ledger = Ledger()
        ledger.append(subscription_id="sub_1", actor="ENGINE", rule_triggered="R1")
        ledger.append(subscription_id="sub_1", actor="ENGINE", rule_triggered="R2")
        ledger.save_jsonl(file_path)

        loaded = Ledger.load_jsonl(file_path)
        assert len(loaded.records) == 2
        assert loaded.verify_chain() is True

    def test_tamper_detection(self, tmp_path: Path):
        """Mutating any line in persisted JSONL must fail chain verification."""
        file_path = tmp_path / "tampered_audit.jsonl"
        ledger = Ledger()
        ledger.append(subscription_id="sub_1", actor="ENGINE", rule_triggered="R1")
        ledger.append(subscription_id="sub_1", actor="ENGINE", rule_triggered="R2")
        ledger.save_jsonl(file_path)

        # Read JSONL lines
        lines = file_path.read_text(encoding="utf-8").strip().split("\n")
        record_data = json.loads(lines[0])
        # Mutate an input field without updating the hash!
        record_data["inputs"]["tampered_key"] = "hacked"
        lines[0] = json.dumps(record_data)

        # Write back tampered content
        file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        # Loading tampered file MUST raise LedgerTamperError
        with pytest.raises(LedgerTamperError, match="broken hash digest|mismatched previous_hash"):
            Ledger.load_jsonl(file_path)
