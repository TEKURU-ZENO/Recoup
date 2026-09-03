import casesJson from '../app/data/cases.json';

export interface CaseRecord {
  case_id: string;
  subscription_id: string;
  customer_name: string;
  amount_due_paise: number;
  failure_code: string;
  instrument_type: string;
  status: string;
  escalation_level: string;
  attempt_count: number;
  phone_number: string | null;
  is_dnd: boolean;
  created_at: string;
  audit_record_count?: number;
}

export interface AuditRecord {
  audit_id: string;
  timestamp_utc: string;
  subscription_id: string;
  actor: string;
  policy_version: string;
  rule_triggered: string;
  inputs: Record<string, unknown>;
  execution_payload: Record<string, unknown>;
  compliance_check: Record<string, unknown>;
  previous_hash: string;
  record_hash: string;
}

interface CasesFixture {
  generated_from: string;
  cases: CaseRecord[];
  audits: Record<string, AuditRecord[]>;
}

export const casesFixture = casesJson as CasesFixture;

export function fixtureCases(): CaseRecord[] {
  return casesFixture.cases;
}
export function fixtureCase(id: string): CaseRecord | undefined {
  return casesFixture.cases.find((c) => c.case_id === id || c.subscription_id === id);
}
export function fixtureAudit(id: string): AuditRecord[] {
  const c = fixtureCase(id);
  return (c && casesFixture.audits[c.case_id]) || casesFixture.audits[id] || [];
}
