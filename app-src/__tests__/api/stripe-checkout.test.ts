import { describe, it, expect, vi, beforeEach } from 'vitest'
import { NextRequest } from 'next/server'

const { state } = vi.hoisted(() => ({
  state: {
    isPaid: false,
    row: { founding_member: false, stripe_customer_id: null as string | null },
    sessionsCreate: vi.fn(async (_params: Record<string, unknown>) => ({ url: 'https://checkout.stripe.com/s' })),
  },
}))

vi.mock('@clerk/nextjs/server', () => ({ auth: async () => ({ userId: 'user_1' }) }))
vi.mock('@/lib/tier', () => ({
  getEffectiveTier: async () => ({ tier: state.isPaid ? 'pro' : 'free', isPaid: state.isPaid, isAgency: false, isTrialActive: false, trialEndsAt: null }),
}))
vi.mock('@/lib/supabase/server', () => ({
  createClient: () => ({
    from: () => ({ select: () => ({ eq: () => ({ maybeSingle: async () => ({ data: state.row, error: null }) }) }) }),
  }),
}))
vi.mock('stripe', () => ({
  default: class { checkout = { sessions: { create: state.sessionsCreate } } },
}))

import { POST } from '@/app/api/stripe/checkout/route'

const post = (body: unknown) =>
  POST(new NextRequest('https://app.strwatch.io/api/stripe/checkout', { method: 'POST', body: JSON.stringify(body) }))

describe('POST /api/stripe/checkout', () => {
  beforeEach(() => {
    process.env.STRIPE_SECRET_KEY = 'sk_test_x'
    process.env.STRIPE_PRICE_PRO = 'price_pro'
    process.env.STRIPE_PRICE_AGENCY = 'price_agency'
    delete process.env.STRIPE_PRICE_FOUNDING
    process.env.NEXT_PUBLIC_APP_URL = 'https://app.strwatch.io'
    state.isPaid = false
    state.row = { founding_member: false, stripe_customer_id: null }
    state.sessionsCreate.mockClear()
  })

  it('returns 409 use_billing_portal for a paying subscriber', async () => {
    state.isPaid = true
    const res = await post({ tier: 'pro' })
    expect(res.status).toBe(409)
    expect(await res.json()).toEqual({ error: 'use_billing_portal' })
    expect(state.sessionsCreate).not.toHaveBeenCalled()
  })

  it('reuses an existing Stripe customer instead of minting a new one', async () => {
    state.row = { founding_member: false, stripe_customer_id: 'cus_existing' }
    const res = await post({ tier: 'pro' })
    expect(res.status).toBe(200)
    const params = state.sessionsCreate.mock.calls[0][0]
    expect(params.customer).toBe('cus_existing')
    expect(params.line_items).toEqual([{ price: 'price_pro', quantity: 1 }])
  })

  it('lets Stripe create the customer when none is stored', async () => {
    const res = await post({ tier: 'pro' })
    expect(res.status).toBe(200)
    const params = state.sessionsCreate.mock.calls[0][0]
    expect(params).not.toHaveProperty('customer')
  })

  it('does not require STRIPE_PRICE_FOUNDING for a pro checkout', async () => {
    const res = await post({ tier: 'pro' })
    expect(res.status).toBe(200)
  })

  it('requires STRIPE_PRICE_FOUNDING only for a founding checkout', async () => {
    state.row = { founding_member: true, stripe_customer_id: null }
    await expect(post({ tier: 'founding' })).rejects.toThrow('STRIPE_PRICE_FOUNDING')
    process.env.STRIPE_PRICE_FOUNDING = 'price_founding'
    const res = await post({ tier: 'founding' })
    expect(res.status).toBe(200)
    const params = state.sessionsCreate.mock.calls[0][0]
    expect(params.metadata).toEqual({ userId: 'user_1', tier: 'pro', founding: 'true' })
  })

  it('rejects founding checkout for non-founders', async () => {
    process.env.STRIPE_PRICE_FOUNDING = 'price_founding'
    const res = await post({ tier: 'founding' })
    expect(res.status).toBe(403)
  })
})
