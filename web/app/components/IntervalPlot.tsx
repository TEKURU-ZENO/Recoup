'use client';

import React, { useId, useState } from 'react';

export interface IntervalRow {
  label: string;
  mean: number;
  ci: number;
  /** Optional explicit bounds; default mean ± ci. */
  low?: number;
  high?: number;
  /** e.g. "+2.37pp ± 1.13pp" */
  valueText: string;
  tooltip?: string;
}

type Sign = 'pos' | 'neg' | 'dim';

function classify(low: number, high: number): Sign {
  if (low > 0) return 'pos';
  if (high < 0) return 'neg';
  return 'dim';
}

const SIGN_LABEL: Record<Sign, string> = {
  pos: 'established (CI clears 0)',
  neg: 'negative (CI below 0)',
  dim: 'directional — CI straddles 0',
};

/**
 * Dot + 95%-CI whisker against a zero line. A delta-to-baseline / emphasis form:
 * the reader's job is to see, per comparison, whether the interval clears zero.
 * Colour encodes that AND every row carries a text label — never colour alone.
 */
export function IntervalPlot({
  rows,
  unitLabel,
  caption,
}: {
  rows: IntervalRow[];
  unitLabel: string;
  caption?: string;
}) {
  const uid = useId();
  const [hover, setHover] = useState<number | null>(null);

  const W = 760;
  const rowH = 46;
  const padTop = 10;
  const axisH = 26;
  const H = padTop + rows.length * rowH + axisH;

  const labelW = 208;
  const valueW = 176;
  const plotX0 = labelW;
  const plotX1 = W - valueW;
  const plotW = plotX1 - plotX0;

  const bounds = rows.map((r) => ({
    lo: r.low ?? r.mean - r.ci,
    hi: r.high ?? r.mean + r.ci,
  }));
  let dMin = Math.min(0, ...bounds.map((b) => b.lo));
  let dMax = Math.max(0, ...bounds.map((b) => b.hi));
  const span = dMax - dMin || 1;
  dMin -= span * 0.08;
  dMax += span * 0.08;

  const sx = (v: number) => plotX0 + ((v - dMin) / (dMax - dMin)) * plotW;
  const zeroX = sx(0);

  const ticks = niceTicks(dMin, dMax, 4);

  return (
    <figure style={{ margin: 0 }}>
      <div style={{ position: 'relative', overflowX: 'auto' }}>
        <svg
          className="iplot"
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          aria-label={`Interval plot: ${rows.map((r) => `${r.label} ${r.valueText}`).join('; ')}`}
          style={{ minWidth: 560 }}
        >
          {/* gridlines + ticks */}
          {ticks.map((t) => (
            <g key={t}>
              <line x1={sx(t)} x2={sx(t)} y1={padTop} y2={padTop + rows.length * rowH} className="axis-line" opacity={0.35} />
              <text x={sx(t)} y={H - 8} textAnchor="middle" className="tick-label">
                {formatTick(t)}
              </text>
            </g>
          ))}
          {/* zero reference */}
          <line x1={zeroX} x2={zeroX} y1={padTop} y2={padTop + rows.length * rowH} className="zero-line" />
          <text x={zeroX} y={H - 8} textAnchor="middle" className="tick-label" style={{ fontWeight: 700 }}>
            0
          </text>

          {rows.map((r, i) => {
            const b = bounds[i];
            const cy = padTop + i * rowH + rowH / 2;
            const sign = classify(b.lo, b.hi);
            const hovered = hover === i;
            return (
              <g
                key={i}
                onMouseEnter={() => setHover(i)}
                onMouseLeave={() => setHover((h) => (h === i ? null : h))}
              >
                <rect x={0} y={padTop + i * rowH} width={W} height={rowH} fill={hovered ? 'rgba(255,255,255,0.03)' : 'transparent'} />
                <text x={0} y={cy - 4} className="row-label">{r.label}</text>
                <text x={0} y={cy + 12} className="val-label">{SIGN_LABEL[sign]}</text>

                {/* whisker */}
                <line x1={sx(b.lo)} x2={sx(b.hi)} y1={cy} y2={cy} className={`whisker s-${sign}`} />
                <line x1={sx(b.lo)} x2={sx(b.lo)} y1={cy - 5} y2={cy + 5} className={`cap s-${sign}`} />
                <line x1={sx(b.hi)} x2={sx(b.hi)} y1={cy - 5} y2={cy + 5} className={`cap s-${sign}`} />
                <circle cx={sx(r.mean)} cy={cy} r={5} className={`s-${sign}-fill`} stroke="var(--surface)" strokeWidth={1.5} />

                <text x={W} y={cy + 4} textAnchor="end" className="val-label" style={{ fill: 'var(--text)', fontSize: 11.5 }}>
                  {r.valueText}
                </text>
              </g>
            );
          })}
        </svg>

        {hover !== null && rows[hover].tooltip && (
          <div
            role="tooltip"
            style={{
              position: 'absolute',
              top: `calc(${((padTop + hover * rowH + rowH) / H) * 100}% + 4px)`,
              left: '4%',
              right: '4%',
              background: 'var(--bg-raised)',
              border: '1px solid var(--border-strong)',
              borderRadius: 8,
              padding: '0.6rem 0.75rem',
              fontFamily: 'var(--font-sans)',
              fontSize: '0.8rem',
              color: 'var(--text-dim)',
              boxShadow: 'var(--shadow-md)',
              pointerEvents: 'none',
              zIndex: 5,
            }}
          >
            <strong style={{ color: 'var(--text)' }}>{rows[hover].label}</strong> — {rows[hover].tooltip}
          </div>
        )}
      </div>

      <div className="iplot-legend" aria-hidden>
        <span><i style={{ background: 'var(--pos)' }} />established (CI clears 0)</span>
        <span><i style={{ background: 'var(--text-dim)' }} />directional (CI straddles 0)</span>
        <span><i style={{ background: 'var(--neg)' }} />negative</span>
      </div>
      {caption && <figcaption className="provenance">{caption}</figcaption>}
      <p className="provenance" style={{ marginTop: '0.3rem' }}>x-axis: {unitLabel}. Bars are 95% confidence intervals of the paired per-seed difference.</p>
    </figure>
  );
}

function niceTicks(min: number, max: number, count: number): number[] {
  const raw = (max - min) / count;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const norm = raw / mag;
  const step = (norm >= 5 ? 5 : norm >= 2 ? 2 : 1) * mag;
  const start = Math.ceil(min / step) * step;
  const out: number[] = [];
  for (let v = start; v <= max + 1e-9; v += step) out.push(Math.round(v * 1e6) / 1e6);
  return out;
}

function formatTick(t: number): string {
  if (Math.abs(t) >= 1000) return (t / 1000).toFixed(0) + 'k';
  if (Number.isInteger(t)) return String(t);
  return t.toFixed(1);
}
