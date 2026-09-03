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
                <td>Compliance & Channel Substitution</td>
                <td style={{ color: 'var(--accent-emerald)' }}><strong>+1.70pp ± 1.48pp</strong></td>
                <td><strong>+1.26pp ± 1.02pp</strong></td>
                <td>Channel substitution: links replace futile retries (+10.5pp on expired cards)</td>
              </tr>
              <tr>
                <td style={{ fontWeight: 600 }}>NaiveBounded → SmartBounded</td>
                <td>Contextual Timing Schedule</td>
                <td><strong>-0.07pp ± 0.54pp</strong></td>
                <td><strong>+0.09pp ± 0.23pp</strong></td>
                <td>Liquidity vs attrition trade-off: fast retry avoids customer attrition cliff</td>
              </tr>
              <tr>
                <td style={{ fontWeight: 600 }}>SmartBounded → SmartBoundedVoice</td>
                <td>Voice Intercept Telephony (>₹5k)</td>
                <td style={{ color: 'var(--accent-emerald)' }}><strong>+3.53pp ± 1.85pp</strong></td>
                <td><strong>+0.79pp ± 0.37pp</strong></td>
                <td>1.70 accounts recovered / seed from 4.55 calls (37.4% conv., target &gt;₹5k)</td>
              </tr>
              <tr style={{ borderTop: '2px solid var(--border-color)', background: 'rgba(16, 185, 129, 0.05)' }}>
                <td style={{ fontWeight: 700 }}>Cumulative System Lift</td>
                <td>Full Autonomous Recovery Agent</td>
                <td style={{ color: 'var(--accent-emerald)', fontWeight: 700 }}><strong>+5.17pp ± 2.45pp</strong></td>
                <td style={{ color: 'var(--accent-emerald)', fontWeight: 700 }}><strong>+2.14pp ± 1.15pp</strong></td>
                <td>₹+23,155 gross capital recovered per batch, -39.5% retries, zero violations</td>
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
                <td>₹218,740.20</td>
                <td>₹226,538.53</td>
                <td>₹226,280.64</td>
                <td style={{ fontWeight: 700, color: 'var(--accent-emerald)' }}>₹241,895.35</td>
              </tr>
              <tr>
                <td>Gateway MDR (2.0%)</td>
                <td>₹4,374.80</td>
                <td>₹4,530.77</td>
                <td>₹4,525.61</td>
                <td>₹4,837.90</td>
              </tr>
              <tr>
                <td>Delivery Spend (SMS/WA/Voice)</td>
                <td>₹57.24</td>
                <td>₹21.80</td>
                <td>₹21.68</td>
                <td>₹44.42</td>
              </tr>
              <tr>
                <td>Contact Churn Fatigue Cost</td>
                <td style={{ color: 'var(--accent-rose)' }}>₹1,518.75</td>
                <td style={{ color: 'var(--accent-emerald)' }}>₹0.00</td>
                <td style={{ color: 'var(--accent-emerald)' }}>₹0.00</td>
                <td>₹204.75</td>
              </tr>
              <tr style={{ fontWeight: 700, background: 'rgba(255, 255, 255, 0.03)' }}>
                <td>Net Recovered Capital</td>
                <td>₹212,789.41</td>
                <td>₹221,985.97</td>
                <td>₹221,733.36</td>
                <td style={{ color: 'var(--accent-cyan)' }}>₹236,808.28</td>
              </tr>
              <tr>
                <td>Net ROI Multiple</td>
                <td>35.7x</td>
                <td>48.8x</td>
                <td>48.8x</td>
                <td><strong>46.6x</strong></td>
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
          <div className="card-title">Channel Substitution</div>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            Substituting futile retries with instant digital links drives significant recovery:
            <ul style={{ marginTop: '0.5rem', paddingLeft: '1.25rem' }}>
              <li><code>card_expired</code>: <strong>+10.5pp ± 5.0pp</strong> (Statistically established)</li>
              <li><code>3ds_dropoff</code>: +4.9pp ± 7.0pp (Directional, straddles zero)</li>
            </ul>
          </div>
        </div>
        <div className="card">
          <div className="card-title">The Deferral Dilemma: Attrition vs Truncation</div>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            Diagnostic sweep across a full 28-day billing cycle reveals two distinct regimes:
            <ul style={{ marginTop: '0.5rem', paddingLeft: '1.25rem' }}>
              <li><strong>0d to 7d</strong>: Constant retries (~340), recovery falls 43.6% &rarr; 40.5% (pure attrition decay)</li>
              <li><strong>14d to 21d</strong>: Horizon truncation drops retries from 346 &rarr; 222, crashing recovery to 34.9%</li>
            </ul>
          </div>
        </div>
        <div className="card">
          <div className="card-title">Voice Telephony: Selection & Sensitivity</div>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            Accounts &ge; ₹5,000 average ₹9,185/case (selection effect):
            <ul style={{ marginTop: '0.5rem', paddingLeft: '1.25rem' }}>
              <li><strong>37.4% conv.</strong>: 1.70 recoveries from 4.55 calls &rarr; ₹15,075 net lift (686x call ROI)</li>
              <li><strong>15.0% conv.</strong>: 0.68 recoveries &rarr; ₹6,121 net lift (41.3x call ROI)</li>
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
