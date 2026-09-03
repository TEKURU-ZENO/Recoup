import React from 'react';
import { IconArrowRight } from './icons';

export function StatTile({
  label,
  value,
  ci,
  sub,
  tone,
  hero,
  href,
}: {
  label: React.ReactNode;
  value: React.ReactNode;
  ci?: React.ReactNode;
  sub?: React.ReactNode;
  tone?: 'pos';
  hero?: boolean;
  href?: string;
}) {
  const cls = `stat ${hero ? 'hero' : ''} ${tone || ''} ${href ? 'link-stat' : ''}`;
  const inner = (
    <>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {ci && <div className="stat-ci">{ci}</div>}
      {sub && <div className="stat-sub">{sub}</div>}
    </>
  );
  return href ? (
    <a className={cls} href={href}>
      {inner}
    </a>
  ) : (
    <div className={cls}>{inner}</div>
  );
}

export function KpiStrip({ withHero, children }: { withHero?: boolean; children: React.ReactNode }) {
  return <div className={`kpi-strip ${withHero ? 'with-hero' : ''}`}>{children}</div>;
}

/** Three tiles read left→right as a story, with arrows between. */
export function Funnel({ tiles }: { tiles: [React.ReactNode, React.ReactNode, React.ReactNode] }) {
  return (
    <div className="funnel">
      {tiles[0]}
      <div className="arrow"><IconArrowRight size={18} /></div>
      {tiles[1]}
      <div className="arrow"><IconArrowRight size={18} /></div>
      {tiles[2]}
    </div>
  );
}
