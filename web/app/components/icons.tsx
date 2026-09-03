/** Hand-rolled 1.5px-stroke icon set — deliberately not lucide/feather. */
import React from 'react';

type P = { size?: number; className?: string };
const base = (size: number): React.SVGProps<SVGSVGElement> => ({
  width: size,
  height: size,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.5,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
});

export const IconCheck = ({ size = 16, className }: P) => (
  <svg {...base(size)} className={className}><path d="M4 12.5l5 5L20 6.5" /></svg>
);
export const IconAlert = ({ size = 16, className }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M12 3.5L22 20H2L12 3.5z" /><path d="M12 10v5" /><path d="M12 17.5h.01" />
  </svg>
);
export const IconArrowRight = ({ size = 16, className }: P) => (
  <svg {...base(size)} className={className}><path d="M4 12h15" /><path d="M13 6l7 6-7 6" /></svg>
);
export const IconHalt = ({ size = 16, className }: P) => (
  <svg {...base(size)} className={className}>
    <circle cx="12" cy="12" r="8.5" /><path d="M8.5 8.5l7 7" />
  </svg>
);
export const IconPulse = ({ size = 16, className }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M2 12h5l3-7 4 14 3-7h5" />
  </svg>
);
export const IconLedger = ({ size = 16, className }: P) => (
  <svg {...base(size)} className={className}>
    <rect x="4" y="3.5" width="16" height="17" rx="2" /><path d="M8 8h8M8 12h8M8 16h5" />
  </svg>
);
