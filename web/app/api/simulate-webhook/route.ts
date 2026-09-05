import { NextResponse } from 'next/server';
import crypto from 'node:crypto';

/**
 * Server-side trigger for the "live webhook" demo beat. Builds a Razorpay-shaped
 * payment.failed event, signs it with the same HMAC-SHA256 scheme the FastAPI
 * backend verifies (rra.gateway.webhooks.WebhookManager), and POSTs it to the
 * running Recovery Agent API. The signing secret stays server-side.
 *
 * This is a real signed request against a real handler — the only thing that
 * isn't "production" is that it originates from this route instead of Razorpay.
 */

export const dynamic = 'force-dynamic';

const API_BASE = (process.env.API_BASE || process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000').replace(/\/$/, '');
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET || 'mocksecret123';

type Scenario = 'card_expired' | 'mandate_revoked';

const SCENARIOS: Record<
  Scenario,
  { code: string; source: string; step: string; reason: string; description: string; amount_paise: number; phone: string }
> = {
  card_expired: {
    code: 'BAD_REQUEST_ERROR',
    source: 'customer',
    step: 'payment_authentication',
    reason: 'card_expired',
    description: 'Saved card has expired',
    amount_paise: 650000,
    phone: '+919876500011',
  },
  mandate_revoked: {
    code: 'BAD_REQUEST_ERROR',
    source: 'customer',
    step: 'mandate_cancellation',
    reason: 'mandate_revoked',
    description: 'Customer revoked the recurring mandate',
    amount_paise: 129900,
    phone: '+919876500022',
  },
};

export async function POST(req: Request) {
  let scenario: Scenario = 'card_expired';
  try {
    const body = await req.json();
    if (body?.scenario === 'mandate_revoked') scenario = 'mandate_revoked';
  } catch {
    // no body — default scenario
  }

  const cfg = SCENARIOS[scenario];
  const nonce = crypto.randomBytes(3).toString('hex');
  const subscriptionId = `sub_demo_${nonce}`;
  const paymentId = `pay_demo_${nonce}`;

  const payload = {
    entity: 'event',
    account_id: `acc_demo_${nonce}`,
    event: 'payment.failed',
    created_at: Math.floor(Date.now() / 1000),
    payload: {
      payment: {
        entity: {
          id: paymentId,
          amount: cfg.amount_paise,
          currency: 'INR',
          subscription_id: subscriptionId,
          contact: cfg.phone,
          error: {
            code: cfg.code,
            source: cfg.source,
            step: cfg.step,
            reason: cfg.reason,
            description: cfg.description,
          },
          notes: { customer_name: 'Live webhook demo' },
        },
      },
    },
  };

  const rawBody = JSON.stringify(payload);
  const signature = crypto.createHmac('sha256', WEBHOOK_SECRET).update(rawBody).digest('hex');

  try {
    const res = await fetch(`${API_BASE}/webhooks/razorpay`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'x-razorpay-signature': signature },
      body: rawBody,
      cache: 'no-store',
    });
    const data = await res.json().catch(() => null);

    if (!res.ok) {
      return NextResponse.json(
        { ok: false, error: data?.detail ?? `Recovery Agent API returned HTTP ${res.status}.` },
        { status: 502 },
      );
    }

    return NextResponse.json({
      ok: true,
      scenario,
      subscription_id: subscriptionId,
      payment_id: paymentId,
      sent: payload,
      result: data,
    });
  } catch {
    return NextResponse.json(
      {
        ok: false,
        error: `Could not reach the Recovery Agent API at ${API_BASE}. Start it with: uvicorn rra.api.main:app --reload`,
      },
      { status: 502 },
    );
  }
}
