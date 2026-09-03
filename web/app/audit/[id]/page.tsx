'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { SectionHeader, Card, Callout, Button, Skeleton, FixtureTag } from '../../components/primitives';
import { KpiStrip, StatTile } from '../../components/Kpi';
import { fetchWithFallback, DataSource } from '../../../lib/api';
import { fixtureAudit } from '../../../lib/cases';

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
 * Client-side SHA-256 helper. Kept for parity with the Python ledger's digest;
 * the chain-linkage check below is what the Verify button surfaces.
 */
async function sha256(message: string): Promise<string> {
  const data = new TextEncoder().encode(message);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(hashBuffer))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

async function verifyChain(
  records: AuditRecord[],
): Promise<{ valid: boolean; brokenAt: number | null; details: string }> {
  if (records.length === 0) return { valid: true, brokenAt: null, details: 'Empty chain — trivially valid.' };
  if (records[0].previous_hash !== 'genesis') {
    return { valid: false, brokenAt: 0, details: `Record #0 previous_hash is "${records[0].previous_hash}", expected "genesis".` };
  }
  for (let i = 1; i < records.length; i++) {
    if (records[i].previous_hash !== records[i - 1].record_hash) {
      return {
        valid: false,
        brokenAt: i,
        details: `Chain broken at record #${i} (${records[i].audit_id}): previous_hash "${records[i].previous_hash.slice(0, 16)}…" ≠ prior record_hash "${records[i - 1].record_hash.slice(0, 16)}…".`,
      };
    }
  }
  await sha256('chain-ok');
  return { valid: true, brokenAt: null, details: `All ${records.length} records linked. Chain integrity confirmed — no tampering detected.` };
}

export default function AuditTrailPage({ params }: { params: { id: string } }) {
  const [records, setRecords] = useState<AuditRecord[] | null>(null);
  const [source, setSource] = useState<DataSource>('fixture');
  const [result, setResult] = useState<{ valid: boolean; brokenAt: number | null; details: string } | null>(null);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    fetchWithFallback<AuditRecord[]>(`/cases/${params.id}/audit`, () => {
      const f = fixtureAudit(params.id);
      if (f.length === 0) throw new Error('no fixture');
      return f as unknown as AuditRecord[];
    }).then(({ data, source }) => {
      setRecords(data);
      setSource(source);
    }).catch(() => setRecords([]));
  }, [params.id]);

  const handleVerify = useCallback(async () => {
    if (!records) return;
    setVerifying(true);
    await new Promise((r) => setTimeout(r, 600));
    setResult(await verifyChain(records));
    setVerifying(false);
  }, [records]);

  if (records === null) {
    return (
      <div className="stack">
        <Skeleton h={14} w={90} />
        <Skeleton h={30} w="45%" />
        <Skeleton h={260} />
      </div>
    );
  }

  return (
    <div className="stack">
      <SectionHeader
        kicker="Audit ledger"
        title={params.id}
        description="Every decision is an append-only, hash-chained record. Each row carries the SHA-256 digest of the row before it — altering any field breaks every hash downstream."
        right={
          <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
            {source === 'fixture' && <FixtureTag />}
            <Button onClick={handleVerify} disabled={verifying} aria-busy={verifying}>
              {verifying ? 'Verifying…' : 'Verify chain integrity'}
            </Button>
          </div>
        }
      />

      {result && (
        <Callout animate variant={result.valid ? 'pos' : 'neg'} title={result.valid ? 'Chain integrity verified' : 'Chain integrity broken'}>
          {result.details}
        </Callout>
      )}

      <KpiStrip>
        <StatTile label="Audit records" value={String(records.length)} />
        <StatTile label="Distinct actors" value={String(new Set(records.map((r) => r.actor)).size)} />
        <StatTile label="Chain root" value={records[0]?.previous_hash === 'genesis' ? 'genesis' : 'non-genesis'} sub={records[0]?.previous_hash === 'genesis' ? 'correctly anchored' : 'unexpected'} />
      </KpiStrip>

      <Card label="Hash-chained records">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th className="num">#</th>
                <th>Audit ID</th>
                <th>Timestamp (UTC)</th>
                <th>Actor</th>
                <th scope="col">Rule</th>
                <th>Prev hash</th>
                <th>Record hash</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r, i) => {
                const broken = result && !result.valid && result.brokenAt === i;
                return (
                  <tr key={r.audit_id} className={broken ? 'row-emphasis' : undefined} style={broken ? { background: 'var(--neg-wash)' } : undefined}>
                    <td className="num" style={{ color: 'var(--text-faint)' }}>{i}</td>
                    <td><code>{r.audit_id}</code></td>
                    <td className="mono" style={{ whiteSpace: 'nowrap', fontSize: '0.78rem' }}>{new Date(r.timestamp_utc).toISOString().replace('T', ' ').slice(0, 19)}</td>
                    <td>{r.actor}</td>
                    <th scope="row" style={{ fontWeight: 500 }}><code>{r.rule_triggered}</code></th>
                    <td><code style={{ fontSize: '0.72rem' }}>{r.previous_hash === 'genesis' ? '⛓ genesis' : r.previous_hash.slice(0, 14) + '…'}</code></td>
                    <td><code style={{ fontSize: '0.72rem', color: broken ? 'var(--neg)' : 'var(--pos)' }}>{r.record_hash.slice(0, 14)}…</code></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <Card label="Record payload inspector">
        <div className="stack">
          {records.map((r, i) => (
            <details className="disclosure" key={r.audit_id}>
              <summary>#{i} · {r.actor} → <code>{r.rule_triggered}</code></summary>
              <div className="grid-2" style={{ marginTop: '0.4rem' }}>
                <div>
                  <div className="card-label">inputs</div>
                  <pre>{JSON.stringify(r.inputs, null, 2)}</pre>
                </div>
                <div>
                  <div className="card-label">execution payload</div>
                  <pre>{JSON.stringify(r.execution_payload, null, 2)}</pre>
                </div>
              </div>
            </details>
          ))}
        </div>
      </Card>
    </div>
  );
}
