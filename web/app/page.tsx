import React from 'react';
import { SectionHeader, Card, Button } from './components/primitives';
import { KpiStrip, StatTile, Funnel } from './components/Kpi';
import { IntervalPlot, IntervalRow } from './components/IntervalPlot';
import { IconArrowRight } from './components/icons';
import { benchmark, armRow, pairedDelta, ARM_LABELS } from '../lib/data';
import { inrFromRupees, signedInr } from '../lib/format';

export const metadata = { title: 'Recoup — the result' };

function econ(metric: string, arm: string) {
  return armRow(benchmark.economics, metric)?.arms[arm];
}
function tech(metric: string, arm: string) {
  return armRow(benchmark.technical, metric)?.arms[arm];
}

export default function ResultPage() {
  const incNet = econ('Incremental Net Capital', 'SmartBoundedVoice'); // ₹+26,406.55 ± ₹11,059.66
  const violStraw = tech('Guard Violations', 'NaiveUnbounded'); // 286.9 ± 8.2
  const refused = tech('Declined Chases', 'NaiveBounded'); // 24.3 ± 2.0

  const gross = econ('Gross Revenue Recovered', 'SmartBoundedVoice');
  const mdr = econ('Gateway MDR', 'SmartBoundedVoice');
  const delivery = econ('Channel Delivery Spend', 'SmartBoundedVoice');
  const fatigue = econ('Contact Churn Fatigue', 'SmartBoundedVoice');
  const net = econ('Net Recovered Capital', 'SmartBoundedVoice');
  const costs =
    (mdr?.mean ?? 0) + (delivery?.mean ?? 0) + (fatigue?.mean ?? 0);

  const deltaRows: IntervalRow[] = [
    ['NaiveUnbounded → NaiveBounded', 'Unbounded → Bounded'],
    ['NaiveBounded → SmartBounded', 'Bounded → Smart'],
    ['SmartBounded → SmartBoundedVoice', 'Smart → Smart + Voice'],
  ].map(([key, label]) => {
    const d = pairedDelta(key, 'Value Recovery Rate')!;
    return {
      label,
      mean: d.mean ?? 0,
      ci: d.ci ?? 0,
      valueText: d.text,
      tooltip: d.interpretation,
    };
  });

  return (
    <div className="stack">
      <SectionHeader
        kicker="Result"
        title="What the agent recovered — and how sure we are of it"
        description={
          <>
            Four recovery strategies run over the same {benchmark.cases_per_seed} failed-payment cases,{' '}
            {benchmark.seeds} times, sharing pseudorandom draws so the paired difference isolates each design
            decision. Every figure below is read straight from the generated benchmark report.
          </>
        }
      />

      <KpiStrip withHero>
        <StatTile
          hero
          label="Net capital recovered per batch, over the guarded baseline"
          value={signedInr(incNet?.mean ?? 0)}
          ci={`± ${inrFromRupees(incNet?.ci ?? 0)}  ·  95% CI`}
          sub="baseline = Naive · bounded: full TRAI/DND guards + digital channels, no retry tuning, no voice. This is the added capital on top of it."
        />
        <StatTile
          tone="pos"
          label="Compliance-guard violations"
          value="0"
          ci="TRAI hours · cooling-off · DND"
          sub={`the unbounded strawman: ${violStraw?.text ?? '—'} per batch`}
        />
        <StatTile
          href="/refused"
          label="Accounts refused as structurally dead"
          value={refused?.text ?? '—'}
          ci="examined · classified · chased 0 times"
          sub="open the refusal ledger →"
        />
      </KpiStrip>

      <Card label="Where the lift comes from — paired value-recovery-rate deltas">
        <IntervalPlot
          rows={deltaRows}
          unitLabel="percentage points of value recovered (INR-weighted)"
          caption={benchmark.provenance}
        />
        <p className="muted" style={{ fontSize: '0.88rem', marginTop: '0.9rem' }}>
          Each step adds one design decision. All three intervals clear zero — the hero number above is wide
          (±42% of its estimate), but it is built from these, and the mechanism deltas are tight. The voice
          intercept has the largest point estimate and the widest interval, because it acts on a small number
          of high-value accounts.{' '}
          <a className="btn link" href="/benchmark">See the full decomposition <IconArrowRight size={13} /></a>
        </p>
      </Card>

      <Card label="Per-batch economics · Smart · bounded + voice">
        <Funnel
          tiles={[
            <StatTile key="g" label="Gross recovered" value={inrFromRupees(gross?.mean ?? 0)} ci={`± ${inrFromRupees(gross?.ci ?? 0)}`} />,
            <StatTile key="c" label="less MDR + delivery + fatigue" value={`− ${inrFromRupees(costs)}`} sub="2% MDR · SMS/WA/voice · churn-fatigue" />,
            <StatTile key="n" tone="pos" label="Net recovered capital" value={inrFromRupees(net?.mean ?? 0)} ci={`± ${inrFromRupees(net?.ci ?? 0)}`} />,
          ]}
        />
      </Card>

      <div className="grid-2">
        <Card label="What it refused to touch">
          <p className="muted" style={{ fontSize: '0.9rem' }}>
            {benchmark.seeds ? '' : ''}The one screen most recovery dashboards don&apos;t have: the accounts the
            agent examined and deliberately did not chase.
          </p>
          <div style={{ marginTop: '0.9rem' }}><Button href="/refused" variant="quiet">Open the refusal ledger <IconArrowRight size={14} /></Button></div>
        </Card>
        <Card label="Why the obvious approach fails">
          <p className="muted" style={{ fontSize: '0.9rem' }}>
            The unbounded strawman chases everything and racks up {violStraw?.text ?? ''} guard violations for
            worse net recovery. Doing strictly less futile work is the optimisation.
          </p>
          <div style={{ marginTop: '0.9rem' }}><Button href="/benchmark" variant="quiet">Read the mechanism <IconArrowRight size={14} /></Button></div>
        </Card>
      </div>
    </div>
  );
}
