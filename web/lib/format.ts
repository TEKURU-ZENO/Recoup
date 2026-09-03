/** Formatting helpers. Rupees are stored as paise (integer) in the API. */

export function inr(paise: number): string {
  return '₹' + (paise / 100).toLocaleString('en-IN', { maximumFractionDigits: 0 });
}

export function inrFromRupees(rupees: number, opts: { decimals?: number } = {}): string {
  return (
    '₹' +
    rupees.toLocaleString('en-IN', {
      minimumFractionDigits: opts.decimals ?? 0,
      maximumFractionDigits: opts.decimals ?? 0,
    })
  );
}

export function signedInr(rupees: number): string {
  const s = rupees < 0 ? '−' : '+';
  return s + inrFromRupees(Math.abs(rupees));
}

export function pp(value: number, digits = 2): string {
  const s = value < 0 ? '−' : '+';
  return `${s}${Math.abs(value).toFixed(digits)}pp`;
}

/** e.g. "+₹26,407 ± ₹11,060" from a MeanCI-like {mean, ci} in rupees. */
export function meanCiInr(mean: number, ci: number): { value: string; interval: string } {
  return { value: signedInr(mean), interval: `± ${inrFromRupees(ci)}` };
}
