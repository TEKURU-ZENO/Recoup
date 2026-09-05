'use client';

import React, { useEffect, useState } from 'react';
import { SectionHeader, Card, StatusBadge, Badge, TableSkeleton, EmptyState, FixtureTag } from '../components/primitives';
import { KpiStrip, StatTile } from '../components/Kpi';
import { LiveWebhookPanel } from '../components/LiveWebhookPanel';
import { fetchWithFallback, DataSource } from '../../lib/api';
import { fixtureCases, CaseRecord } from '../../lib/cases';
import { inr } from '../../lib/format';

export default function CasesPage() {
  const [cases, setCases] = useState<CaseRecord[] | null>(null);
  const [source, setSource] = useState<DataSource>('fixture');

  const load = () => {
    fetchWithFallback<CaseRecord[]>('/cases', fixtureCases).then(({ data, source }) => {
      setCases(data);
      setSource(source);
    });
  };

  useEffect(load, []);

  const atRisk = (cases ?? []).reduce((a, c) => a + c.amount_due_paise, 0);
  const halted = (cases ?? []).filter((c) => c.status === 'halted' || c.status === 'declined').length;

  return (
    <div className="stack">
      <SectionHeader
        kicker="Portfolio"
        title="Failed subscription cases"
        description="Operational drill-down: every case the agent is currently working, its classified root cause and FSM state."
        right={source === 'fixture' ? <FixtureTag /> : undefined}
      />

      <LiveWebhookPanel onSimulated={load} />

      {cases === null ? (
        <Card><TableSkeleton rows={6} cols={6} /></Card>
      ) : cases.length === 0 ? (
        <EmptyState title="No active cases">
          The Recovery Agent API is running but holds no cases yet. Post a <code>payment.failed</code> webhook
          or run <code>make demo</code> to populate the portfolio.
        </EmptyState>
      ) : (
        <>
          <KpiStrip>
            <StatTile label="Revenue at risk" value={inr(atRisk)} sub={`${cases.length} open cases`} />
            <StatTile label="Open cases" value={String(cases.length)} />
            <StatTile label="Halted / declined" value={String(halted)} sub="refused as unrecoverable" />
          </KpiStrip>

          <Card label={`Cases (${cases.length})`}>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Case</th>
                    <th>Customer</th>
                    <th className="num">Amount</th>
                    <th scope="col">Root cause</th>
                    <th>Escalation</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {cases.map((c) => (
                    <tr key={c.case_id}>
                      <td><a className="btn link" href={`/case/${c.subscription_id}`}>{c.case_id}</a></td>
                      <td>{c.customer_name}</td>
                      <td className="num">{inr(c.amount_due_paise)}</td>
                      <th scope="row" style={{ fontWeight: 500 }}><Badge>{c.failure_code.replace(/_/g, ' ')}</Badge></th>
                      <td><StatusBadge value={c.escalation_level} /></td>
                      <td><StatusBadge value={c.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="provenance">
              {source === 'fixture'
                ? 'Source: committed fixture from the offline deterministic engine — synthetic identities.'
                : 'Source: live Recovery Agent API on :8000.'}
            </p>
          </Card>
        </>
      )}
    </div>
  );
}
