/**
 * Every screen prefers the live API and falls back to the committed fixture
 * when it is unreachable — but the fallback is always *surfaced*, never silent.
 * A project whose whole identity is not overstating results cannot quietly
 * substitute stand-in data.
 */
export type DataSource = 'live' | 'fixture';

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, '') || 'http://localhost:8000';

export interface Loaded<T> {
  data: T;
  source: DataSource;
}

export async function fetchWithFallback<T>(
  path: string,
  fixture: () => T,
  { timeoutMs = 1500 }: { timeoutMs?: number } = {},
): Promise<Loaded<T>> {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), timeoutMs);
    const res = await fetch(`${API_BASE}${path}`, { signal: ctrl.signal });
    clearTimeout(t);
    if (!res.ok) throw new Error(String(res.status));
    const data = (await res.json()) as T;
    // API returns [] until webhooks are posted — treat empty as "nothing live".
    if (Array.isArray(data) && data.length === 0) throw new Error('empty');
    return { data, source: 'live' };
  } catch {
    return { data: fixture(), source: 'fixture' };
  }
}

export async function pingApi(timeoutMs = 1200): Promise<boolean> {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), timeoutMs);
    const res = await fetch(`${API_BASE}/health`, { signal: ctrl.signal });
    clearTimeout(t);
    return res.ok;
  } catch {
    return false;
  }
}
