import { describe, it, expect, vi, beforeEach } from 'vitest'
import { NextRequest } from 'next/server'

const { state } = vi.hoisted(() => ({
  state: {
    event: null as unknown,
    activeSubs: 0,
    upserts: [] as Record<string, unknown>[],
    lookupUserId: null as string | null,
    listCalls: [] as unknown[],
  },
}))

vi.mock('@/lib/supabase/server', () => ({
  createClient: () => ({
    from: () => ({
      upsert: async (payload: Record<string, unknown>) => { state.upserts.push(payload); return { error: null } },
      select: () => ({ eq: () => ({ maybeSingle: async () => ({ data: state.lookupUserId ? { user_id: state.lookupUserId } : null, error: null }) }) }),
    }),
  }),
}))
vi.mock('stripe', () => ({
  default: class {
    webhooks = { constructEvent: () => state.event }
    subscriptions = {
      list: async (params: unknown) => { state.listCalls.push(params); return { data: Array.from({ length: state.activeSubs }, (_, i) => ({ id: `sub_${i}` })) } },
    }
  },
}))

import { POST } from '@/app/api/stripe/webhook/route'

const post = () =>
  POST(new NextRequest('https://app.strwatch.io/api/stripe/webhook', { method: 'POST', body: '{}', headers: { 'stripe-signature': 'sig' } }))

describe('POST /api/stripe/webhook customer.subscription.deleted', () => {
  beforeEach(() => {
    process.env.STRIPE_SECRET_KEY = 'sk_test_x'
    process.env.STRIPE_WEBHOOK_SECRET = 'whsec_x'
    state.upserts = []
    state.listCalls = []
    state.activeSubs = 0
    state.lookupUserId = null
  })

  it('downgrades to free when no other active subscription remains', async () => {
    state.event = { type: 'customer.subscription.deleted', data: { object: { customer: 'cus_1', metadata: { userId: 'user_1' } } } }
    const res = await post()
    expect(res.status).toBe(200)
    expect(state.listCalls[0]).toEqual({ customer: 'cus_1', status: 'active', limit: 1 })
    expect(state.upserts).toHaveLength(1)
    expect(state.upserts[0]).toMatchObject({ user_id: 'user_1', tier: 'free', trial_ends_at: null })
  })

  it('skips the downgrade while another subscription is still active', async () => {
    state.activeSubs = 1
    state.event = { type: 'customer.subscription.deleted', data: { object: { customer: 'cus_1', metadata: { userId: 'user_1' } } } }
    const res = await post()
    expect(res.status).toBe(200)
    expect(await res.json()).toEqual({ received: true, skipped: 'active_subscription_remains' })
    expect(state.upserts).toHaveLength(0)
  })

  it('resolves legacy subscriptions by customer id before downgrading', async () => {
    state.lookupUserId = 'user_legacy'
    state.event = { type: 'customer.subscription.deleted', data: { object: { customer: { id: 'cus_2' }, metadata: {} } } }
    await post()
    expect(state.upserts[0]).toMatchObject({ user_id: 'user_legacy', tier: 'free' })
  })
})
