/**
 * Typed access to the generated fixtures in app/data/.
 *
 * These files are written by `python scripts/export_web_data.py` (wired into
 * `make bench` / `make shadow`) straight from docs/benchmark-report.md and
 * docs/shadow-decisions.jsonl. Nothing here is hand-typed — if a number looks
 * wrong, re-run the exporter, don't edit JSON.
 */
import benchmarkJson from '../app/data/benchmark.json';
import shadowJson from '../app/data/shadow-decisions.json';

export interface MeanCI {
  mean?: number;
  ci?: number;
  low?: number;
  high?: number;
  clears_zero?: boolean;
  text: string;
}

export interface PairedDelta extends MeanCI {
  comparison: string;
  metric: string;
  unit: 'pp' | 'inr' | 'count';
  delta: string;
  interpretation: string;
}

export interface ArmRow {
  metric: string;
  arms: Record<string, MeanCI>;
}

export interface FailureMode {
  failure_code: string;
  batch_total: number;
  rates: Record<string, number | null>;
  mechanism: string;
  lift: MeanCI | null;
}

export interface Benchmark {
  generated_from: string;
  seeds: number | null;
  cases_per_seed: number | null;
  provenance: string;
  paired_deltas: PairedDelta[];
  economics: ArmRow[];
  technical: ArmRow[];
  failure_modes: FailureMode[];
}

export interface ShadowEvent {
  event_id: string;
  payment_id: string;
  is_mapped: boolean;
  failure_code: string | null;
  unmapped_reason: string | null;
  proposed_action: string | null;
  rule_triggered: string | null;
  scheduled_at: string | null;
  is_declined_chase: boolean;
  is_legally_compliant: boolean;
}

export interface Shadow {
  generated_from: string;
  total_events: number;
  mapped_events: number;
  taxonomy_coverage_pct: number;
  legal_compliance_pct: number;
  refused_count: number;
  refused_pct: number;
  refused_by_code: Record<string, number>;
  refused: ShadowEvent[];
  events: ShadowEvent[];
}

export const benchmark = benchmarkJson as Benchmark;
export const shadow = shadowJson as Shadow;

export const ARMS = [
  'NaiveUnbounded',
  'NaiveBounded',
  'SmartBounded',
  'SmartBoundedVoice',
] as const;

export const ARM_LABELS: Record<string, string> = {
  NaiveUnbounded: 'Naive · unbounded',
  NaiveBounded: 'Naive · bounded',
  SmartBounded: 'Smart · bounded',
  SmartBoundedVoice: 'Smart · bounded + voice',
};

/** Find one arm-column row by a substring of its metric name. */
export function armRow(rows: ArmRow[], needle: string): ArmRow | undefined {
  return rows.find((r) => r.metric.toLowerCase().includes(needle.toLowerCase()));
}

/** Find one paired delta by substrings of comparison + metric. */
export function pairedDelta(comparison: string, metric: string): PairedDelta | undefined {
  return benchmark.paired_deltas.find(
    (d) =>
      d.comparison.toLowerCase().includes(comparison.toLowerCase()) &&
      d.metric.toLowerCase().includes(metric.toLowerCase()),
  );
}
