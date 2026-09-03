'use client';

import React from 'react';

export default function BenchmarkPage() {
  return (
    <div>
      <h1 style={{ marginBottom: '1.5rem', fontSize: '1.875rem' }}>
        Benchmark Comparison: 4-Arm Empirical Decomposition & Economics
      </h1>

      <div
        className="card"
        style={{
          marginBottom: '2rem',
          borderLeft: '4px solid var(--accent-amber)',
          background: 'rgba(245, 158, 11, 0.05)',
        }}
      >
        <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>Calibration Notice</div>
        <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          Absolute recovery levels (≈52–57%) are uncalibrated against production cohorts (where industry dunning typically runs 15–30%).
          The meaningful metrics are the <strong>paired deltas between arms under identical Common Random Number (CRN) draws</strong>, which cancel shared variance to isolate causal mechanisms.
        </div>
      </div>

      {/* Paired-Delta Summary */}
      <div className="card" style={{ marginBottom: '2rem' }}>
        <div className="card-title">4-Arm Paired-Delta Decomposition (20 Seeds, 215 Cases/Seed, CRN-Paired)</div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Comparison</th>
                <th>Isolated Variable</th>
                <th>Paired Value Δ (INR)</th>
                <th>Paired Case Δ (Count)</th>
                <th>Empirical Mechanism</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style={{ fontWeight: 600 }}>NaiveUnbounded → NaiveBounded</td>
                <td>Bounded Guards & Links</td>
                <td><strong>+1.65pp ± 1.51pp</strong></td>
                <td><strong>+1.07pp ± 0.96pp</strong></td>
                <td>Channel substitution: links replace futile retries on dead cards</td>
              </tr>
              <tr>
                <td style={{ fontWeight: 600 }}>NaiveBounded → SmartBounded</td>
                <td>Decoupled Dunning Ladder</td>
                <td style={{ color: 'var(--accent-emerald)' }}><strong>+2.37pp ± 1.13pp</strong></td>
                <td style={{ color: 'var(--accent-emerald)' }}><strong>+2.91pp ± 0.89pp</strong></td>
                <td>Decoupled dunning: Day-1 nudge captures intent, 28th auto-debit captures liquidity (-71 retries)</td>
              </tr>
              <tr>
                <td style={{ fontWeight: 600 }}>SmartBounded → SmartBoundedVoice</td>
                <td>Voice Intercept Telephony (>₹5k)</td>
                <td style={{ color: 'var(--accent-emerald)' }}><strong>+3.91pp ± 2.05pp</strong></td>
                <td><strong>+0.88pp ± 0.42pp</strong></td>
                <td>5.8 calls cost ₹29.00 and yield ₹16,632 net capital (37.4% conv., target &gt;₹5k)</td>
              </tr>
              <tr style={{ borderTop: '2px solid var(--border-color)', background: 'rgba(16, 185, 129, 0.05)' }}>
                <td style={{ fontWeight: 700 }}>Cumulative System Lift</td>
                <td>Full Autonomous Recovery Agent</td>
                <td style={{ color: 'var(--accent-emerald)', fontWeight: 700 }}><strong>+7.92pp ± 2.45pp</strong></td>
                <td style={{ color: 'var(--accent-emerald)', fontWeight: 700 }}><strong>+4.86pp ± 1.25pp</strong></td>
                <td>₹+35,613 net capital recovered per batch, -49.7% retries, zero violations</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Unit Economics Table */}
      <div className="card" style={{ marginBottom: '2rem' }}>
        <div className="card-title">Unit Economics & Margin Accounting (Per Batch of 215 Cases)</div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Economic Metric</th>
                <th>NaiveUnbounded</th>
                <th>NaiveBounded</th>
                <th>SmartBounded</th>
                <th>SmartBoundedVoice</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Gross Revenue Recovered</td>
                <td>₹171,952.85</td>
                <td>₹179,408.16</td>
                <td>₹189,383.90</td>
                <td style={{ fontWeight: 700, color: 'var(--accent-emerald)' }}>₹206,651.16</td>
              </tr>
              <tr>
                <td>Gateway MDR (2.0%)</td>
                <td>₹3,439.05</td>
                <td>₹3,588.16</td>
                <td>₹3,787.67</td>
                <td>₹4,133.02</td>
              </tr>
              <tr>
                <td>Delivery Spend (SMS/WA/Voice)</td>
                <td>₹70.54</td>
                <td>₹33.15</td>
                <td>₹34.74</td>
                <td>₹63.74</td>
              </tr>
              <tr>
                <td>Contact Churn Fatigue Cost</td>
                <td style={{ color: 'var(--accent-rose)' }}>₹1,863.00</td>
                <td style={{ color: 'var(--accent-emerald)' }}>₹0.00</td>
                <td style={{ color: 'var(--accent-emerald)' }}>₹0.00</td>
                <td>₹261.00</td>
              </tr>
              <tr style={{ fontWeight: 700, background: 'rgba(255, 255, 255, 0.03)' }}>
                <td>Net Recovered Capital</td>
                <td>₹166,580.26</td>
                <td>₹175,786.85</td>
                <td>₹185,561.49</td>
                <td style={{ color: 'var(--accent-cyan)' }}>₹202,193.41</td>
              </tr>
              <tr>
                <td>Incremental Net Capital vs Bounded</td>
                <td style={{ color: 'var(--accent-rose)' }}>-₹9,206.59</td>
                <td>₹0.00 (Baseline)</td>
                <td style={{ color: 'var(--accent-emerald)', fontWeight: 600 }}>+₹9,774.64</td>
                <td style={{ color: 'var(--accent-cyan)', fontWeight: 700 }}>+₹26,406.56</td>
              </tr>
              <tr>
                <td>Return on Incremental Spend</td>
                <td style={{ color: 'var(--accent-rose)' }}>Negative</td>
                <td>Baseline</td>
                <td style={{ color: 'var(--accent-emerald)' }}>6,147.5x incremental</td>
                <td style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>573.5x incremental</td>
              </tr>
              <tr>
                <td>Wasted Spend on Dead Accounts</td>
                <td style={{ color: 'var(--accent-rose)' }}>₹8.12</td>
                <td style={{ color: 'var(--accent-emerald)' }}>₹0.00</td>
                <td style={{ color: 'var(--accent-emerald)' }}>₹0.00</td>
                <td style={{ color: 'var(--accent-emerald)' }}>₹0.00</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Analytical Takeaways */}
      <div className="grid-3" style={{ marginBottom: '2rem' }}>
        <div className="card">
          <div className="card-title">Decoupled Dunning Discovery</div>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            Decoupling customer communication from auto-debits breaks the scheduling null:
            <ul style={{ marginTop: '0.5rem', paddingLeft: '1.25rem' }}>
              <li><strong>+2.37pp Value Lift / +2.91pp Cases</strong> over NaiveBounded</li>
              <li>Day-1 link captures fresh intent; 28th debit captures peak liquidity</li>
              <li>Eliminates <strong>71.3 futile retries</strong> before debit</li>
            </ul>
          </div>
        </div>
        <div className="card">
          <div className="card-title">Complementary Funnel Dynamics</div>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            Interventions operate on opposite ends of the balance distribution:
            <ul style={{ marginTop: '0.5rem', paddingLeft: '1.25rem' }}>
              <li><strong>Decoupled Links (+2.91pp Cases)</strong>: Drives volume at the long tail (~₹1,200 median)</li>
              <li><strong>Voice Telephony (+3.91pp Value)</strong>: Drives value at the top of the book (&ge; ₹5,000)</li>
            </ul>
          </div>
        </div>
        <div className="card">
          <div className="card-title">Voice Telephony: Absolute Economics</div>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            High-value targeting (&ge; ₹5,000 averages ₹9,185/case):
            <ul style={{ marginTop: '0.5rem', paddingLeft: '1.25rem' }}>
              <li><strong>5.8 calls (₹29.00 spent)</strong> &rarr; <strong>₹16,632 net capital</strong></li>
              <li>Stress test at 15% conv: recovers ~₹6,200 net</li>
              <li><strong>Break-Even</strong>: <strong>0.055% conversion</strong> (1 recovery per 1,800 calls)</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Schema Conformance & Policy Legality Check */}
      <div className="card">
        <div className="card-title">Schema Conformance & Policy Legality Check (400 Synthetic-Realistic Events)</div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Taxonomy Coverage</th>
                <th>Policy Legality</th>
                <th>Refused Unrecoverable Chases</th>
                <th>Active Recoveries Routed</th>
                <th>Unmapped Gateway Anomalies</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong style={{ color: 'var(--accent-emerald)' }}>99.0%</strong> (396/400)</td>
                <td><strong style={{ color: 'var(--accent-emerald)' }}>100.0%</strong></td>
                <td><strong style={{ color: 'var(--accent-amber)' }}>30 cases</strong> (7.5%)</td>
                <td><strong>366 cases</strong> (91.5%)</td>
                <td><code>suspected_fraud_velocity_limit</code> (flagged)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
