import './globals.css';
import React from 'react';
import type { Metadata, Viewport } from 'next';
import { Space_Grotesk, Manrope, JetBrains_Mono } from 'next/font/google';
import { Shell } from './components/Shell';

const display = Space_Grotesk({ subsets: ['latin'], weight: ['500', '600', '700'], variable: '--font-space-grotesk', display: 'swap' });
const sans = Manrope({ subsets: ['latin'], weight: ['400', '500', '600'], variable: '--font-manrope', display: 'swap' });
const mono = JetBrains_Mono({ subsets: ['latin'], weight: ['400', '500'], variable: '--font-jetbrains-mono', display: 'swap' });

export const metadata: Metadata = {
  title: 'Recoup — recovery agent results',
  description:
    'What an autonomous dunning agent recovered on failed recurring payments, how sure we are of it, and what it deliberately refused to chase.',
  icons: { icon: '/icon.svg' },
};

export const viewport: Viewport = {
  themeColor: '#0b0c0e',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${sans.variable} ${mono.variable}`}>
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
