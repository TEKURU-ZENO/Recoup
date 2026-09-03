"""Hash-chained, tamper-evident audit ledger.

Appends AuditRecord instances where each record includes the SHA-256 hash
of the preceding record, forming an immutable tamper-evident chain.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rra.domain.models import AuditRecord


class LedgerTamperError(ValueError):
    """Raised when ledger chain verification fails due to tampering."""
    pass


class Ledger:
    """Hash-chained audit log ledger."""

    def __init__(self, records: list[AuditRecord] | None = None) -> None:
        self._records: list[AuditRecord] = records or []

    @property
    def records(self) -> list[AuditRecord]:
        return list(self._records)

    @property
    def head_hash(self) -> str:
        return self._records[-1].record_hash if self._records else "genesis"

    def append(
        self,
        subscription_id: str,
        actor: str,
        rule_triggered: str,
        policy_version: str = "v2026.1.0",
        inputs: dict[str, Any] | None = None,
        execution_payload: dict[str, Any] | None = None,
        compliance_check: dict[str, Any] | None = None,
    ) -> AuditRecord:
        """Append a new record to the chain linked to current head_hash."""
        record = AuditRecord(
            subscription_id=subscription_id,
            actor=actor,
            policy_version=policy_version,
            rule_triggered=rule_triggered,
            inputs=inputs or {},
            execution_payload=execution_payload or {},
            compliance_check=compliance_check or {},
            previous_hash=self.head_hash,
        )
        self._records.append(record)
        return record

    def verify_chain(self) -> bool:
        """Walk the chain and verify that all hashes and parent pointers are valid.

        Returns:
            True if chain is intact.

        Raises:
            LedgerTamperError: If any record hash or parent pointer is tampered.
        """
        expected_prev = "genesis"
        for idx, rec in enumerate(self._records):
            if rec.previous_hash != expected_prev:
                raise LedgerTamperError(
                    f"Record at index {idx} ({rec.audit_id}) has mismatched previous_hash: "
                    f"expected '{expected_prev}', got '{rec.previous_hash}'."
                )

            # Re-verify self hash calculation
            recomputed = AuditRecord(**rec.model_dump(exclude={"record_hash"})).record_hash
            if rec.record_hash != recomputed:
                raise LedgerTamperError(
                    f"Record at index {idx} ({rec.audit_id}) has broken hash digest: "
                    f"stored '{rec.record_hash}', recomputed '{recomputed}'."
                )

            expected_prev = rec.record_hash

        return True

    def for_subscription(self, subscription_id: str) -> list[AuditRecord]:
        """Return all audit records for a given subscription ID."""
        return [r for r in self._records if r.subscription_id == subscription_id]

    def save_jsonl(self, filepath: str | Path) -> None:
        """Persist records to an append-only JSONL file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for rec in self._records:
                f.write(rec.model_dump_json() + "\n")

    @classmethod
    def load_jsonl(cls, filepath: str | Path) -> Ledger:
        """Load records from a JSONL file and verify chain integrity."""
        path = Path(filepath)
        if not path.exists():
            return cls()

        records: list[AuditRecord] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    records.append(AuditRecord(**data))

        ledger = cls(records=records)
        ledger.verify_chain()
        return ledger
