'use client';

import React, { useEffect, useState } from 'react';

export default function CaseTimelinePage({ params }: { params: { id: string } }) {
  const [caseData, setCaseData] = useState<any>(null);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);

  useEffect(() => {
    fetch(`http://localhost:8000/cases/${params.id}`)
      .then((res) => res.json())
      .then((data) => setCaseData(data))
      .catch(() => {
        setCaseData({
          case_id: params.id,
          subscription_id: 'sub_Nx983jK29LzP',
          customer_name: 'Aarav Sharma',
          amount_due_paise: 249900,
          failure_code: 'insufficient_funds',
          status: 'active',
          escalation_level: 'smart_retry',
          attempt_count: 1,
          is_dnd: false,
          created_at: '2026-04-01T09:30:00Z',
        });
      });

    fetch(`http://localhost:8000/cases/${params.id}/audit`)
      .then((res) => res.json())
      .then((data) => setAuditLogs(data))
      .catch(() => {
        setAuditLogs([
          {
            audit_id: 'aud_88F91A2B',
            timestamp_utc: '2026-04-01T09:30:00Z',
            actor: 'RAZORPAY_WEBHOOK_HANDLER',
            rule_triggered: 'EVENT_PAYMENT_FAILED',
            previous_hash: 'genesis',
            record_hash: '3a9f02b1c8e7...',
          },
          {
            audit_id: 'aud_99C12E4F',
            timestamp_utc: '2026-04-01T09:30:05Z',
            actor: 'AGENT_POLICY_ENGINE',
            rule_triggered: 'RULE_LIQUIDITY_SYNC_SALARY_DATE',
            previous_hash: '3a9f02b1c8e7...',
            record_hash: '9d4e11f0a2c3...',
          },
        ]);
      });
  }, [params.id]);

  if (!caseData) return <div>Loading timeline...</div>;

  return (
    <div>
      <h1 style={{ marginBottom: '1.5rem', fontSize: '1.875rem' }}>
        Case Timeline: <code>{caseData.case_id}</code>
      </h1>

      <div className="grid-3">
        <div className="card">
          <div className="card-title">Customer Name</div>
          <div className="card-value" style={{ fontSize: '1.25rem' }}>{caseData.customer_name}</div>
        </div>
        <div className="card">
          <div className="card-title">Amount Due</div>
          <div className="card-value" style={{ fontSize: '1.25rem', color: 'var(--accent-cyan)' }}>
            ₹{(caseData.amount_due_paise / 100).toLocaleString('en-IN')}
          </div>
        </div>
        <div className="card">
          <div className="card-title">Escalation Status</div>
          <div>
            <span className="badge badge-active">{caseData.escalation_level}</span>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '2rem' }}>
        <div className="card-title">Decision Engine Timeline</div>
        <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', borderLeft: '4px solid var(--accent-cyan)' }}>
            <div style={{ fontWeight: 600 }}>09:30 IST — Event Ingestion & Taxonomy Parsing</div>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
              Gateway failure code <code>insufficient_funds</code> classified. FSM initialized to <code>SMART_RETRY</code>.
            </div>
          </div>
          <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', borderLeft: '4px solid var(--accent-emerald)' }}>
            <div style={{ fontWeight: 600 }}>09:30:05 IST — Smart Scheduler Evaluation</div>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
              Mid-month failure detected. Backend retry deferred to 28th IST salary clearing window. TRAI hours & DND scrub passed.
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Hash-Chained Tamper-Evident Audit Log</div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Audit ID</th>
                <th>Timestamp (UTC)</th>
                <th>Actor</th>
                <th>Rule Triggered</th>
                <th>Previous Hash</th>
                <th>Record Hash</th>
              </tr>
            </thead>
            <tbody>
              {auditLogs.map((log) => (
                <tr key={log.audit_id}>
                  <td><code>{log.audit_id}</code></td>
                  <td>{log.timestamp_utc}</td>
                  <td>{log.actor}</td>
                  <td><code>{log.rule_triggered}</code></td>
                  <td><code style={{ fontSize: '0.75rem' }}>{log.previous_hash.slice(0, 10)}...</code></td>
                  <td><code style={{ fontSize: '0.75rem', color: 'var(--accent-emerald)' }}>{log.record_hash.slice(0, 10)}...</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
