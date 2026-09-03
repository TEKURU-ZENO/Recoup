import './globals.css';
import React from 'react';

export const metadata = {
  title: 'Revenue Recovery Agent — Executive Dashboard',
  description: 'Automated AI Revenue Recovery for Indian Recurring Payment Systems',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="container">
          <header className="navbar">
            <div className="brand">Revenue Recovery Agent</div>
            <nav className="nav-links">
              <a href="/">Batch Overview</a>
              <a href="/benchmark">Benchmark Report</a>
              <a href="/audit/demo">Audit Trail</a>
            </nav>
          </header>
          <main>{children}</main>
        </div>
      </body>
    </html>
  );
}
