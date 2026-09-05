'use client';

import React, { useEffect, useState } from 'react';
import { SectionHeader, Card, StatusBadge, Skeleton, FixtureTag, Button } from '../../components/primitives';
import { KpiStrip, StatTile } from '../../components/Kpi';
import { fetchWithFallback, DataSource } from '../../../lib/api';
import { fixtureCase, fixtureAudit, CaseRecord, AuditRecord } from '../../../lib/cases';
import { inr } from '../../../lib/format';

export default function CaseTimelinePage({ params }: { params: { id: string } }) {
  const [c, setC] = useState<CaseRecord | null>(null);
  const [audit, setAudit] = useState<AuditRecord[]>([]);
  const [source, setSource] = useState<DataSource>('fixture');
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    fetchWithFallback<CaseRecord>(`/cases/${params.id}`, () => {
      const f = fixtureCase(params.id);
      if (!f) throw new Error('no fixture');
      return f;
    })
      .then(({ data, source }) => {
        setC(data);
        setSource(source);
      })
      .catch(() => setMissing(true));

    fetchWithFallback<AuditRecord[]>(`/cases/${params.id}/audit`, () => fixtureAudit(params.id)).then(({ data }) =>
      setAudit(data),
    );
  }, [params.id]);

  if (missing) {
    return (
      <div>
        <SectionHeader kicker="Case" title="Case not found" description={`No case "${params.id}" in the live API or the committed fixture.`} />
        <Button href="/cases" variant="quiet">Back to portfolio</Button>
      </div>
    );
  }
  if (!c) {
    return (
      <div className="stack">
        <Skeleton h={14} w={100} />
        <Skeleton h={30} w="40%" />
        <div className="kpi-strip"><Skeleton h={110} /><Skeleton h={110} /><Skeleton h={110} /></div>
        <Skeleton h={240} />
      </div>
    );
  }

  return (
    <div className="stack">
      <SectionHeader
        kicker="Case"
        title={c.case_id}
        description={<>Subscription <code>{c.subscription_id}</code> · classified <code>{c.failure_code}</code></>}
        right={source === 'fixture' ? <FixtureTag /> : undefined}
      />

      <KpiStrip>
        <StatTile label="Customer" value={c.customer_name} sub={c.phone_number ?? 'no phone on file'} />
        <StatTile label="Amount due" value={inr(c.amount_due_paise)} />
        <StatTile label="Escalation state" value={<StatusBadge value={c.escalation_level} />} sub={`${c.attempt_count} actions taken · status ${c.status}`} />
      </KpiStrip>

      <Card label="Hash-chained decision & audit trail">
        {audit.length === 0 ? (
          <p className="muted">No audit records for this case.</p>
        ) : (
          <div className="timeline">
            {audit.map((r, i) => (
              <div className="tl-item" key={r.audit_id}>
                <span className={`tl-node ${r.actor.includes('WEBHOOK') ? 'info' : i === audit.length - 1 ? 'pos' : ''}`} />
                <div className="tl-time">{new Date(r.timestamp_utc).toISOString().replace('T', ' ').slice(0, 19)} UTC</div>
                <div className="tl-title">{r.actor} · <code>{r.rule_triggered}</code></div>
                <div className="tl-body">
                  {Object.entries(r.execution_payload).length > 0 && (
                    <span className="mono" style={{ fontSize: '0.8rem' }}>
                      {Object.entries(r.execution_payload).map(([k, v]) => `${k}=${v ?? '—'}`).join('  ')}
                    </span>
                  )}
                  <div style={{ marginTop: '0.35rem', fontSize: '0.72rem', color: 'var(--text-faint)' }} className="mono">
                    {r.previous_hash === 'genesis' ? '⛓ genesis' : `prev ${r.previous_hash.slice(0, 12)}…`} → {r.record_hash.slice(0, 12)}…
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
        <div style={{ marginTop: '1.2rem' }}>
          {/* The audit ledger is keyed by subscription_id, not case_id — use that so the
              lookup resolves for both live cases and the offline-engine fixture. */}
          <Button href={`/audit/${c.subscription_id}`} variant="quiet">Open full audit ledger &amp; verify chain</Button>
        </div>
      </Card>
    </div>
  );
}
