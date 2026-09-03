'use client';

import React, { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { pingApi } from '../../lib/api';

const NAV = [
  { href: '/', label: 'Result' },
  { href: '/benchmark', label: 'Why it works' },
  { href: '/refused', label: 'What we refused' },
  { href: '/cases', label: 'Portfolio' },
];

function NavLinks() {
  const path = usePathname();
  return (
    <nav className="nav">
      {NAV.map((n) => {
        const active = n.href === '/' ? path === '/' : path.startsWith(n.href);
        return (
          <a key={n.href} href={n.href} data-active={active} aria-current={active ? 'page' : undefined}>
            {n.label}
          </a>
        );
      })}
    </nav>
  );
}

function DataStatus() {
  const [live, setLive] = useState<boolean | null>(null);
  useEffect(() => {
    let alive = true;
    pingApi().then((ok) => alive && setLive(ok));
    return () => {
      alive = false;
    };
  }, []);
  if (live === null) return <span className="datasrc" aria-hidden><span className="datasrc-dot" style={{ background: 'var(--text-faint)' }} />checking…</span>;
  return live ? (
    <span className="datasrc" title="Connected to the local Recovery Agent API on :8000">
      <span className="datasrc-dot live" />live data
    </span>
  ) : (
    <span className="datasrc" title="API on :8000 not reachable — screens render from the committed benchmark + shadow-run fixtures">
      <span className="datasrc-dot fixture" />fixture data · API offline
    </span>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <>
      <header className="shell-header">
        <a className="brand" href="/">
          <span className="brand-dot" />
          Recoup
        </a>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.9rem', flexWrap: 'wrap' }}>
          <NavLinks />
          <DataStatus />
        </div>
      </header>
      <main className="main">{children}</main>
    </>
  );
}
