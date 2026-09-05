'use client';

import React, { useState } from 'react';
import { Card, Button, Callout, Badge } from './primitives';
import { IconArrowRight } from './icons';

type Scenario = 'card_expired' | 'mandate_revoked';

interface SimResult {
  ok: boolean;
  error?: string;
  scenario?: Scenario;
  subscription_id?: string;
  result?: {
    case_id: string;
    failure_code: string;
    escalation_level: string;
    case_status: string;
    next_action: { action_type: string; channel: string | null; scheduled_at: string } | null;
  };
}

/**
 * Fires a real HMAC-SHA256-signed payment.failed webhook at the local Recovery
 * Agent API via /api/simulate-webhook (server-side — the signing secret never
 * reaches the browser), then lets the caller refetch the portfolio so the new
 * case appears without a page reload.
 */
export function LiveWebhookPanel({ onSimulated }: { onSimulated?: () => void }) {
  const [pending, setPending] = useState<Scenario | null>(null);
  const [result, setResult] = useState<SimResult | null>(null);

  const fire = async (scenario: Scenario) => {
    setPending(scenario);
    setResult(null);
    try {
      const res = await fetch('/api/simulate-webhook', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ scenario }),
      });
      const data = (await res.json()) as SimResult;
      setResult(data);
      if (data.ok) onSimulated?.();
    } catch {
      setResult({ ok: false, error: 'Request to /api/simulate-webhook failed.' });
    } finally {
      setPending(null);
    }
  };

  const r = result?.result;

  return (
    <Card label="Send a live webhook">
      <p className="muted" style={{ fontSize: '0.9rem', marginBottom: '1rem' }}>
        Fires a real, HMAC-SHA256-signed <code>payment.failed</code> event at the running Recovery
        Agent API on <code>:8000</code> — the same signature check, taxonomy classifier and policy
        engine that would process production traffic. Requires the API running locally
        (<code>uvicorn rra.api.main:app --reload</code>).
      </p>
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        <Button onClick={() => fire('card_expired')} disabled={pending !== null} aria-busy={pending === 'card_expired'}>
          {pending === 'card_expired' ? 'Sending…' : 'Simulate: card expired'}
        </Button>
        <Button
          variant="quiet"
          onClick={() => fire('mandate_revoked')}
          disabled={pending !== null}
          aria-busy={pending === 'mandate_revoked'}
        >
          {pending === 'mandate_revoked' ? 'Sending…' : 'Simulate: mandate revoked'}
        </Button>
      </div>

      {result && (
        <div style={{ marginTop: '1rem' }}>
          {!result.ok || !r ? (
            <Callout variant="neg" title="Webhook failed">
              {result.error ?? 'Unknown error.'}
            </Callout>
          ) : (
            <Callout
              animate
              variant={r.next_action ? 'pos' : 'warn'}
              title={r.next_action ? 'Signature verified · action dispatched' : 'Signature verified · refused at Level 0'}
            >
              <div className="mono" style={{ fontSize: '0.82rem', marginBottom: '0.5rem' }}>
                <code>{result.subscription_id}</code> ·{' '}
                <Badge>{r.failure_code.replace(/_/g, ' ')}</Badge> ·{' '}
                <Badge tone={r.next_action ? 'accent' : 'neg'}>{r.escalation_level.replace(/_/g, ' ')}</Badge>
              </div>
              <div style={{ fontSize: '0.88rem' }}>
                {r.next_action ? (
                  <>
                    Policy engine dispatched <strong>{r.next_action.action_type.replace(/_/g, ' ')}</strong>
                    {r.next_action.channel ? ` via ${r.next_action.channel}` : ''}.
                  </>
                ) : (
                  <>Policy engine refused to chase — case halted at Level 0. Zero fees spent, zero contact attempted.</>
                )}
              </div>
              <div style={{ marginTop: '0.6rem' }}>
                <Button variant="link" href={`/case/${result.subscription_id}`}>
                  View case &amp; audit trail <IconArrowRight size={13} />
                </Button>
              </div>
            </Callout>
          )}
        </div>
      )}
    </Card>
  );
}
