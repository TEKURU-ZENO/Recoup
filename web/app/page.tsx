'use client';

import React, { useEffect, useState } from 'react';

interface CaseData {
  case_id: string;
  subscription_id: string;
  customer_name: string;
  amount_due_paise: number;
  failure_code: string;
  status: string;
  escalation_level: string;
  attempt_count: number;
  created_at: string;
}

export default function BatchPage() {
  const [cases, setCases] = useState<CaseData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:8000/cases')
      .then((res) => res.json())
      .then((data) => {
        setCases(data);
        setLoading(false);
      })
      .catch(() => {
        setCases([
          {
            case_id: 'case_101',
            subscription_id: 'sub_Nx983jK29LzP',
            customer_name: 'Aarav Sharma',
            amount_due_paise: 249900,
            failure_code: 'insufficient_funds',
            status: 'active',
            escalation_level: 'smart_retry',
            attempt_count: 1,
            created_at: '2026-04-01T09:30:00Z',
          },
          {
            case_id: 'case_102',
            subscription_id: 'sub_Pq452mR88KxM',
            customer_name: 'Diya Patel',
            amount_due_paise: 650000,
            failure_code: 'card_expired',
            status: 'p2p_scheduled',
            escalation_level: 'voice_intercept',
            attempt_count: 2,
            created_at: '2026-04-01T10:15:00Z',
          },
          {
            case_id: 'case_103',
            subscription_id: 'sub_Zk991aB33YyT',
            customer_name: 'Rahul Kumar',
            amount_due_paise: 120000,
            failure_code: 'mandate_revoked',
            status: 'declined',
            escalation_level: 'terminal_halt',
            attempt_count: 0,
            created_at: '2026-04-01T11:00:00Z',
          },
        ]);
        setLoading(false);
      });
  }, []);

  const totalAtRisk = cases.reduce((acc, c) => acc + c.amount_due_paise, 0) / 100;
  const declinedCount = cases.filter((c) => c.status === 'declined' || c.status === 'halted').length;

  return (
    <div>
      <h1 style={{ marginBottom: '1.5rem', fontSize: '1.875rem' }}>Portfolio Batch Overview</h1>
      
      <div className="grid-3">
        <div className="card">
          <div className="card-title">Total Revenue at Risk</div>
          <div className="card-value" style={{ color: 'var(--accent-cyan)' }}>
            ₹{totalAtRisk.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
        </div>
        <div className="card">
          <div className="card-title">Active Portfolio Cases</div>
          <div className="card-value">{cases.length}</div>
        </div>
        <div className="card">
          <div className="card-title">Declined / Halted Chases</div>
          <div className="card-value" style={{ color: 'var(--accent-amber)' }}>{declinedCount}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Failed Subscription Cases</div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Case ID</th>
                <th>Customer</th>
                <th>Amount (INR)</th>
                <th>Failure Root Cause</th>
                <th>Escalation Level</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr key={c.case_id}>
                  <td><code>{c.case_id}</code></td>
                  <td>{c.customer_name}</td>
                  <td>₹{(c.amount_due_paise / 100).toLocaleString('en-IN')}</td>
                  <td><code>{c.failure_code}</code></td>
                  <td><span className="badge badge-active">{c.escalation_level}</span></td>
                  <td><span className={`badge badge-${c.status}`}>{c.status}</span></td>
                  <td>
                    <a href={`/case/${c.case_id}`} className="btn" style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}>
                      View Timeline
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
