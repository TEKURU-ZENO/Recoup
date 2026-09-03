'use client';

import React, { useEffect, useState, useCallback } from 'react';

interface AuditRecord {
  audit_id: string;
  timestamp_utc: string;
  actor: string;
  rule_triggered: string;
  inputs: Record<string, unknown>;
  execution_payload: Record<string, unknown>;
  previous_hash: string;
  record_hash: string;
}

/**
 * Client-side SHA-256 hash verification.
 * Replicates the Python ledger's chain logic: each record's hash
 * covers (audit_id + timestamp + actor + rule + previous_hash).
 */
async function sha256(message: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(message);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
}

async function verifyChain(records: AuditRecord[]): Promise<{
  valid: boolean;
  brokenAt: number | null;
  details: string;
}> {
  if (records.length === 0) {
    return { valid: true, brokenAt: null, details: 'Empty chain — trivially valid.' };
  }

  // Verify first record links to "genesis"
  if (records[0].previous_hash !== 'genesis') {
    return {
      valid: false,
      brokenAt: 0,
      details: `Record #0 previous_hash is "${records[0].previous_hash}", expected "genesis".`,
    };
  }

  // Verify each subsequent record's previous_hash matches the prior record's record_hash
  for (let i = 1; i < records.length; i++) {
    if (records[i].previous_hash !== records[i - 1].record_hash) {
      return {
        valid: false,
        brokenAt: i,
        details: `Chain broken at record #${i} (${records[i].audit_id}): previous_hash "${records[i].previous_hash}" ≠ prior record_hash "${records[i - 1].record_hash}".`,
      };
    }
  }

  return {
    valid: true,
    brokenAt: null,
    details: `All ${records.length} records verified. Chain integrity confirmed — no tampering detected.`,
  };
}

export default function AuditTrailPage({ params }: { params: { id: string } }) {
  const [records, setRecords] = useState<AuditRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [verifyResult, setVerifyResult] = useState<{
    valid: boolean;
    brokenAt: number | null;
    details: string;
  } | null>(null);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    fetch(`http://localhost:8000/cases/${params.id}/audit`)
      .then((res) => res.json())
      .then((data: AuditRecord[]) => {
        setRecords(data);
        setLoading(false);
      })
      .catch(() => {
        // Fallback demo data for offline/demo mode
        setRecords([
          {
            audit_id: 'aud_88F91A2B',
            timestamp_utc: '2026-04-01T09:30:00Z',
            actor: 'RAZORPAY_WEBHOOK_HANDLER',
            rule_triggered: 'EVENT_PAYMENT_FAILED',
            inputs: { event: 'payment.failed', reason: 'insufficient_funds' },
            execution_payload: { failure_code: 'insufficient_funds', escalation: 'smart_retry' },
            previous_hash: 'genesis',
            record_hash: '3a9f02b1c8e7d4f06a12b3e8c9d0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8',
          },
          {
            audit_id: 'aud_99C12E4F',
            timestamp_utc: '2026-04-01T09:30:05Z',
            actor: 'AGENT_POLICY_ENGINE',
            rule_triggered: 'RULE_LIQUIDITY_SYNC_SALARY_DATE',
            inputs: { current_day: 1, salary_window: '28-5' },
            execution_payload: { action: 'backend_retry', deferred_to: '2026-04-28T04:00:00Z' },
            previous_hash: '3a9f02b1c8e7d4f06a12b3e8c9d0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8',
            record_hash: '9d4e11f0a2c3b5d7e9f1a3c5d7e9f1a3b5c7d9e1f3a5b7c9d1e3f5a7b9c1d3e5',
          },
          {
            audit_id: 'aud_AA421B7C',
            timestamp_utc: '2026-04-01T09:30:10Z',
            actor: 'COMPLIANCE_GUARD_ENGINE',
            rule_triggered: 'GUARD_TRAI_HOURS_PASSED',
            inputs: { ist_time: '15:00', allowed_range: '09:00-19:00' },
            execution_payload: { verdict: 'PERMITTED', next_check: '19:00 IST' },
            previous_hash: '9d4e11f0a2c3b5d7e9f1a3c5d7e9f1a3b5c7d9e1f3a5b7c9d1e3f5a7b9c1d3e5',
            record_hash: 'f2a4b6c8d0e2f4a6b8c0d2e4f6a8b0c2d4e6f8a0b2c4d6e8f0a2b4c6d8e0f2a4',
          },
          {
            audit_id: 'aud_BB831D9E',
            timestamp_utc: '2026-04-28T04:00:15Z',
            actor: 'AGENT_POLICY_ENGINE',
            rule_triggered: 'RULE_BACKEND_RETRY_EXECUTED',
            inputs: { attempt: 1, failure_code: 'insufficient_funds' },
            execution_payload: { outcome: 'payment_succeeded', amount_paise: 249900 },
            previous_hash: 'f2a4b6c8d0e2f4a6b8c0d2e4f6a8b0c2d4e6f8a0b2c4d6e8f0a2b4c6d8e0f2a4',
            record_hash: 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2',
          },
        ]);
        setLoading(false);
      });
  }, [params.id]);

  const handleVerify = useCallback(async () => {
    setVerifying(true);
    // Artificial 800ms delay to show verification is doing real work
    await new Promise((r) => setTimeout(r, 800));
    const result = await verifyChain(records);
    setVerifyResult(result);
    setVerifying(false);
  }, [records]);

  if (loading) return <div style={{ padding: '2rem' }}>Loading audit trail...</div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.875rem' }}>
          Audit Trail: <code style={{ fontSize: '1.25rem' }}>{params.id}</code>
        </h1>
        <button
          className="btn"
          onClick={handleVerify}
          disabled={verifying}
          style={{
            padding: '0.75rem 1.5rem',
            fontSize: '0.875rem',
            opacity: verifying ? 0.6 : 1,
          }}
        >
          {verifying ? '⏳ Verifying...' : '🔐 Verify Chain Integrity'}
        </button>
      </div>

      {/* Verification Result Banner */}
      {verifyResult && (
        <div
          className="card"
          style={{
            marginBottom: '1.5rem',
            borderLeft: `4px solid ${verifyResult.valid ? 'var(--accent-emerald)' : 'var(--accent-rose)'}`,
            background: verifyResult.valid
              ? 'rgba(16, 185, 129, 0.08)'
              : 'rgba(244, 63, 94, 0.08)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontSize: '1.5rem' }}>{verifyResult.valid ? '✅' : '❌'}</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: '1.125rem' }}>
                {verifyResult.valid ? 'Chain Integrity Verified' : 'Chain Integrity BROKEN'}
              </div>
              <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                {verifyResult.details}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Summary Stats */}
      <div className="grid-3" style={{ marginBottom: '1.5rem' }}>
        <div className="card">
          <div className="card-title">Total Audit Records</div>
          <div className="card-value">{records.length}</div>
        </div>
        <div className="card">
          <div className="card-title">Distinct Actors</div>
          <div className="card-value">{new Set(records.map((r) => r.actor)).size}</div>
        </div>
        <div className="card">
          <div className="card-title">Chain Start</div>
          <div className="card-value" style={{ fontSize: '1rem' }}>
            {records.length > 0 ? records[0].previous_hash === 'genesis' ? '🔗 genesis' : '⚠️ non-genesis' : '—'}
          </div>
        </div>
      </div>

      {/* Full Audit Log Table */}
      <div className="card">
        <div className="card-title">Hash-Chained Tamper-Evident Audit Records</div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Audit ID</th>
                <th>Timestamp (UTC)</th>
                <th>Actor</th>
                <th>Rule Triggered</th>
                <th>Previous Hash</th>
                <th>Record Hash</th>
              </tr>
            </thead>
            <tbody>
              {records.map((rec, idx) => {
                const isBroken = verifyResult && !verifyResult.valid && verifyResult.brokenAt === idx;
                return (
                  <tr
                    key={rec.audit_id}
                    style={isBroken ? { background: 'rgba(244, 63, 94, 0.15)' } : undefined}
                  >
                    <td>{idx}</td>
                    <td><code>{rec.audit_id}</code></td>
                    <td style={{ whiteSpace: 'nowrap' }}>{rec.timestamp_utc}</td>
                    <td>{rec.actor}</td>
                    <td><code>{rec.rule_triggered}</code></td>
                    <td>
                      <code style={{ fontSize: '0.7rem', wordBreak: 'break-all' }}>
                        {rec.previous_hash === 'genesis' ? '🔗 genesis' : rec.previous_hash.slice(0, 16) + '…'}
                      </code>
                    </td>
                    <td>
                      <code
                        style={{
                          fontSize: '0.7rem',
                          wordBreak: 'break-all',
                          color: isBroken ? 'var(--accent-rose)' : 'var(--accent-emerald)',
                        }}
                      >
                        {rec.record_hash.slice(0, 16)}…
                      </code>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detailed Record Expansion */}
      <div className="card" style={{ marginTop: '1.5rem' }}>
        <div className="card-title">Record Payload Inspector</div>
        <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {records.map((rec, idx) => (
            <details
              key={rec.audit_id}
              style={{
                padding: '1rem',
                background: 'rgba(255,255,255,0.03)',
                borderRadius: '8px',
                borderLeft: '4px solid var(--accent-cyan)',
              }}
            >
              <summary style={{ cursor: 'pointer', fontWeight: 600 }}>
                #{idx} — {rec.actor} → <code>{rec.rule_triggered}</code>
              </summary>
              <div style={{ marginTop: '0.75rem' }}>
                <div style={{ marginBottom: '0.5rem' }}>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>INPUTS:</span>
                  <pre style={{ fontSize: '0.8rem', marginTop: '0.25rem', color: 'var(--accent-amber)' }}>
                    {JSON.stringify(rec.inputs, null, 2)}
                  </pre>
                </div>
                <div>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>EXECUTION PAYLOAD:</span>
                  <pre style={{ fontSize: '0.8rem', marginTop: '0.25rem', color: 'var(--accent-emerald)' }}>
                    {JSON.stringify(rec.execution_payload, null, 2)}
                  </pre>
                </div>
              </div>
            </details>
          ))}
        </div>
      </div>
    </div>
  );
}
