import React from 'react';

/* ---- SectionHeader --------------------------------------------------- */
export function SectionHeader({
  kicker,
  title,
  description,
  as = 'h1',
  right,
}: {
  kicker?: string;
  title: string;
  description?: React.ReactNode;
  as?: 'h1' | 'h2';
  right?: React.ReactNode;
}) {
  const Tag = as;
  return (
    <header className="section-header">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          {kicker && <div className="kicker">{kicker}</div>}
          <Tag>{title}</Tag>
        </div>
        {right}
      </div>
      {description && <p>{description}</p>}
    </header>
  );
}

/* ---- Card ---------------------------------------------------------- */
export function Card({
  label,
  children,
  className = '',
  style,
}: {
  label?: string;
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <section className={`card ${className}`} style={style}>
      {label && <div className="card-label">{label}</div>}
      {children}
    </section>
  );
}

/* ---- Callout ----------------------------------------------------- */
export function Callout({
  variant = 'neutral',
  title,
  children,
  animate = false,
}: {
  variant?: 'neutral' | 'warn' | 'pos' | 'neg';
  title?: string;
  children: React.ReactNode;
  animate?: boolean;
}) {
  const v = variant === 'neutral' ? '' : variant;
  return (
    <div className={`callout ${v} ${animate ? 'enter' : ''}`}>
      {title && <div className="callout-title">{title}</div>}
      <div>{children}</div>
    </div>
  );
}

/* ---- Badge ----------------------------------------------------- */
const STATUS_MAP: Record<string, 'pos' | 'warn' | 'neg' | 'info' | 'accent' | ''> = {
  active: 'accent',
  smart_retry: 'accent',
  voice_intercept: 'info',
  p2p_scheduled: 'info',
  settled: 'pos',
  recovered: 'pos',
  declined: 'warn',
  terminal_halt: 'neg',
  halted: 'neg',
  mandate_revoked: 'neg',
};

export function Badge({ children, tone }: { children: React.ReactNode; tone?: 'pos' | 'warn' | 'neg' | 'info' | 'accent' }) {
  return <span className={`badge ${tone || ''}`}>{children}</span>;
}

export function StatusBadge({ value }: { value: string }) {
  const tone = STATUS_MAP[value] ?? '';
  return <span className={`badge ${tone}`}>{value.replace(/_/g, ' ')}</span>;
}

/* ---- Delta ---------------------------------------------------- */
export function Delta({ text, positive }: { text: string; positive?: boolean }) {
  const tone = positive === undefined ? '' : positive ? 'pos' : 'neg';
  return <span className={`num badge ${tone}`}>{text}</span>;
}

/* ---- Button (also renders as link) --------------------------- */
export function Button({
  variant = 'solid',
  href,
  children,
  ...rest
}: {
  variant?: 'solid' | 'quiet' | 'link';
  href?: string;
  children: React.ReactNode;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const cls = `btn ${variant}`;
  if (href) {
    return (
      <a className={cls} href={href}>
        {children}
      </a>
    );
  }
  return (
    <button className={cls} {...rest}>
      {children}
    </button>
  );
}

/* ---- Skeleton ----------------------------------------------- */
export function Skeleton({ h = 16, w = '100%', style }: { h?: number | string; w?: number | string; style?: React.CSSProperties }) {
  return <div className="skel" style={{ height: h, width: w, ...style }} />;
}

export function TableSkeleton({ rows = 5, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="stack" aria-hidden>
      <Skeleton h={30} />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} style={{ display: 'grid', gap: '0.6rem', gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
          {Array.from({ length: cols }).map((__, j) => (
            <Skeleton key={j} h={18} />
          ))}
        </div>
      ))}
    </div>
  );
}

/* ---- EmptyState ------------------------------------------- */
export function EmptyState({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}

/* ---- fixture tag ---------------------------------------- */
export function FixtureTag() {
  return <span className="tag-fixture" title="Rendered from the committed fixture — the live API was not reachable">fixture</span>;
}
