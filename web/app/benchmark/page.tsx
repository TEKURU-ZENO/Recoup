import React from 'react';
import { SectionHeader, Card, Callout } from '../components/primitives';
import { IntervalPlot, IntervalRow } from '../components/IntervalPlot';
import { benchmark, ARMS, ARM_LABELS } from '../../lib/data';

export const metadata = { title: 'Recoup — why it works' };

const SHORT: Record<string, string> = {
  'NaiveUnbounded → NaiveBounded': 'Unbounded → Bounded',
  'NaiveBounded → SmartBounded': 'Bounded → Smart',
  'SmartBounded → SmartBoundedVoice': 'Smart → Smart + Voice',
};

function deltaRows(metric: string): IntervalRow[] {
  return benchmark.paired_deltas
    .filter((d) => d.metric.toLowerCase().includes(metric.toLowerCase()) && d.mean !== undefined)
    .map((d) => ({
      label: SHORT[d.comparison] ?? d.comparison,
      mean: d.mean ?? 0,
      ci: d.ci ?? 0,
      valueText: d.text,
      tooltip: d.interpretation,
    }));
}

export default function BenchmarkPage() {
  const valueRows = deltaRows('Value Recovery Rate');
  const caseRows = deltaRows('Case Resolution Rate');

  const fmLifts: IntervalRow[] = benchmark.failure_modes
    .filter((f) => f.lift && f.lift.mean !== undefined)
    .map((f) => ({
      label: f.failure_code,
      mean: f.lift!.mean ?? 0,
      ci: f.lift!.ci ?? 0,
      valueText: `${(f.lift!.mean ?? 0) >= 0 ? '+' : ''}${f.lift!.mean}pp ± ${f.lift!.ci}pp`,
      tooltip: f.mechanism.replace(/\*\*/g, '').replace(/\*/g, ''),
    }));

  return (
    <div className="stack">
      <SectionHeader
        kicker="Why it works"
        title="Four arms, one difference at a time"
        description="Each arm adds a single design decision to the one before it. Under common random numbers the paired per-seed difference cancels shared portfolio variance, so a narrow interval that clears zero is a real causal effect."
      />

      <Callout variant="warn" title="Calibration notice">
        Absolute recovery levels (~41–49%) sit at the optimistic end of directional industry ranges
        (passive email ~15–25%, retries + branched dunning ~25–40%, omni-channel ~35–45%). They are a
        property of the outcome model, not a validated match to a production cohort, and production
        calibration is Phase&nbsp;1 of the rollout. The claim is the paired deltas between arms — everything
        drawn below.
      </Callout>

      <Card label="Paired delta — value recovery rate (INR-weighted)">
        <IntervalPlot rows={valueRows} unitLabel="percentage points of INR recovered" caption={benchmark.provenance} />
      </Card>

      <Card label="Paired delta — case resolution rate (count)">
        <IntervalPlot rows={caseRows} unitLabel="percentage points of cases resolved" />
        <p className="muted" style={{ fontSize: '0.88rem', marginTop: '0.8rem' }}>
          The case delta and the value delta point in complementary directions: the decoupled dunning ladder
          resolves proportionally more small accounts (long tail), while the voice intercept adds little case
          count but the most value (top of book).
        </p>
      </Card>

      <Card label="Failure-mode disaggregation">
        <p className="muted" style={{ fontSize: '0.9rem', marginBottom: '1rem' }}>
          Two failure modes carry a measurable paired lift. <code>card_expired</code> is statistically
          established; <code>3ds_dropoff</code> is directional only — its interval straddles zero, and the plot
          says so.
        </p>
        <IntervalPlot rows={fmLifts} unitLabel="percentage points, paired lift vs unbounded" />
        <div className="table-wrap" style={{ marginTop: '1.2rem' }}>
          <table>
            <thead>
              <tr>
                <th scope="col">Failure root cause</th>
                <th className="num">Batch total</th>
                {ARMS.map((a) => (
                  <th key={a} className="num">{ARM_LABELS[a]}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {benchmark.failure_modes.map((f) => (
                <tr key={f.failure_code}>
                  <th scope="row"><code>{f.failure_code}</code></th>
                  <td className="num">{f.batch_total}</td>
                  {ARMS.map((a) => (
                    <td key={a} className="num">{f.rates[a] === null ? '—' : `${f.rates[a]!.toFixed(1)}%`}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card label="Unit economics & cost accounting — per batch, mean ± 95% CI">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Economic metric</th>
                {ARMS.map((a) => (
                  <th key={a} className="num">{ARM_LABELS[a]}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {benchmark.economics.map((row) => {
                const emphasis = /^(Net Recovered Capital|Incremental Net Capital)/.test(row.metric);
                return (
                  <tr key={row.metric} className={emphasis ? 'row-emphasis' : undefined}>
                    <th scope="row">{row.metric}</th>
                    {ARMS.map((a) => (
                      <td key={a} className="num">{row.arms[a]?.text ?? '—'}</td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="muted" style={{ fontSize: '0.88rem', marginTop: '0.9rem' }}>
          Stated as an absolute pairing, not a ratio: <strong>₹1.59 more</strong> channel spend (SmartBounded)
          buys <strong>+₹9,775 ± ₹4,754</strong> net capital; <strong>₹30.59 more</strong> including voice buys{' '}
          <strong>+₹26,407 ± ₹11,060</strong>. No return-multiple is shown — a ratio on a ~₹1.59 denominator is
          a vanity number.
        </p>
        <p className="provenance">
          MDR 2.0% on settlements · SMS ₹0.25 · WhatsApp ₹0.50 · voice ₹5.00 · failed retries ₹0.00 · churn
          fatigue 1.5% hazard × ₹3,000 LTV on contacts &gt; 2 or DND.
        </p>
      </Card>

      <Card label="Per-arm technical summary">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Metric</th>
                {ARMS.map((a) => (
                  <th key={a} className="num">{ARM_LABELS[a]}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {benchmark.technical.map((row) => (
                <tr key={row.metric}>
                  <th scope="row">{row.metric}</th>
                  {ARMS.map((a) => (
                    <td key={a} className="num">{row.arms[a]?.text ?? '—'}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid-2">
        <Card label="Decoupled dunning ladder">
          <p className="muted" style={{ fontSize: '0.9rem' }}>
            Standard ladders couple customer contact to backend auto-debits, so deferring the retry to payday
            also delays the message 12–18 days and intent decays. Decoupling them — Day-1 digital nudge, Day-28
            auto-debit — captures both fresh intent and peak liquidity: +2.37pp ± 1.13pp value, +2.91pp ± 0.89pp
            cases, −71.3 futile retries.
          </p>
        </Card>
        <Card label="Voice intercept — real economics, honest variance">
          <p className="muted" style={{ fontSize: '0.9rem' }}>
            5.8 calls per batch at ₹5.00 each recover a net{' '}
            {benchmark.paired_deltas.find((d) => d.metric.includes('Net Value Lift'))?.text ?? '₹16,632 ± ₹9,212'}.
            The wide interval is real — the target accounts (≥ ₹5,000) are heavy-tailed and n is small. It stays
            accretive down to 0.055% conversion.
          </p>
        </Card>
      </div>
    </div>
  );
}
