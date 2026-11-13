import { describe, it, expect, vi, beforeEach } from 'vitest'

// ---- supabase mock -------------------------------------------------------
type Row = { user_id: string; tier: string; stripe_customer_id: string | null; trial_ends_at: string | null }
let rows: Row[] = []
// Every select chain's filters and every update, for assertions.
const selectFilters: { op: string; args: unknown[] }[] = []
const updates: { payload: Record<string, unknown>; filters: { op: string; args: unknown[] }[] }[] = []

function applyFilters(data: Row[], filters: { op: string; args: unknown[] }[]): Row[] {
  return data.filter(r =>
    filters.every(f => {
      const [col, val] = f.args as [keyof Row, unknown]
      switch (f.op) {
        case 'neq': return r[col] !== val
        case 'eq': return r[col] === val
        case 'is': return r[col] === val
        case 'lt': return r[col] !== null && String(r[col]) < String(val)
        default: return true
      }
    })
  )
}

function makeBuilder() {
  const b: Record<string, unknown> = {}
  const filters: { op: string; args: unknown[] }[] = []
  let mode: 'select' | 'update' = 'select'
  let payload: Record<string, unknown> = {}
  let range: [number, number] = [0, Infinity]
  const filter = (op: string) => vi.fn((...args: unknown[]) => { filters.push({ op, args }); return b })
  b.select = vi.fn(() => { mode = 'select'; return b })
  b.update = vi.fn((p: Record<string, unknown>) => { mode = 'update'; payload = p; return b })
  b.neq = filter('neq'); b.eq = filter('eq'); b.is = filter('is'); b.lt = filter('lt')
  b.order = vi.fn(() => b)
  b.range = vi.fn((from: number, to: number) => { range = [from, to]; return b })
  b.then = (onOk: (v: unknown) => unknown, onErr?: (e: unknown) => unknown) => {
    const run = async () => {
      if (mode === 'update') {
        updates.push({ payload, filters: [...filters] })
        for (const r of applyFilters(rows, filters)) Object.assign(r, payload)
        return { error: null }
      }
      selectFilters.push(...filters)
      const data = applyFilters(rows, filters).slice(range[0], range[1] + 1)
      return { data, error: null }
    }
    return run().then(onOk, onErr)
  }
  return b
}
vi.mock('@/lib/supabase/server', () => ({ createClient: () => ({ from: () => makeBuilder() }) }))

// ---- clerk mock ----------------------------------------------------------
vi.mock('@clerk/nextjs/server', () => ({
  clerkClient: async () => ({
    users: { getUser: async (id: string) => ({ primaryEmailAddress: { emailAddress: `${id}@example.com` } }) },
  }),
}))

// ---- stripe mock ---------------------------------------------------------
// email -> customers; customer id -> has active subscription
const { stripeState } = vi.hoisted(() => ({
  stripeState: { customersByEmail: {} as Record<string, string[]>, activeCustomers: new Set<string>() },
}))
vi.mock('@/lib/stripe', () => ({
  getStripe: () => ({
    customers: {
      search: async ({ query }: { query: string }) => {
        const email = /email:'(.*)'/.exec(query)?.[1] ?? ''
        return { data: (stripeState.customersByEmail[email] || []).map(id => ({ id })) }
      },
    },
    subscriptions: {
      list: async ({ customer }: { customer: string }) => ({
        data: stripeState.activeCustomers.has(customer) ? [{ id: 'sub_1' }] : [],
      }),
    },
  }),
}))

import { GET } from '@/app/api/cron/tiers/route'
import { NextRequest } from 'next/server'

const past = new Date(Date.now() - 86_400_000).toISOString()
const future = new Date(Date.now() + 86_400_000).toISOString()

function request(query = '') {
  return new NextRequest(`http://localhost/api/cron/tiers${query}`, {
    headers: { authorization: 'Bearer test-secret' },
  })
}

beforeEach(() => {
  rows = []
  selectFilters.length = 0
  updates.length = 0
  stripeState.customersByEmail = {}
  stripeState.activeCustomers = new Set()
  process.env.CRON_SECRET = 'test-secret'
})

describe('GET /api/cron/tiers', () => {
  it('401 without secret, 500 when CRON_SECRET unset', async () => {
    expect((await GET(new NextRequest('http://localhost/api/cron/tiers'))).status).toBe(401)
    delete process.env.CRON_SECRET
    expect((await GET(request())).status).toBe(500)
  })

  it('selects only non-free, no-stripe-customer, expired-trial rows and downgrades them', async () => {
    rows = [
      { user_id: 'expired', tier: 'pro', stripe_customer_id: null, trial_ends_at: past },
      { user_id: 'active', tier: 'pro', stripe_customer_id: null, trial_ends_at: future },
      { user_id: 'paid', tier: 'pro', stripe_customer_id: 'cus_p', trial_ends_at: past },
      { user_id: 'free', tier: 'free', stripe_customer_id: null, trial_ends_at: past },
      { user_id: 'agency', tier: 'agency', stripe_customer_id: null, trial_ends_at: null },
    ]
    const body = await (await GET(request())).json()
    expect(body).toEqual({ downgraded: 1, backfilled: 0, errors: 0 })

    expect(selectFilters.map(f => f.op)).toEqual(expect.arrayContaining(['neq', 'is', 'lt']))
    expect(selectFilters.find(f => f.op === 'neq')?.args).toEqual(['tier', 'free'])
    expect(selectFilters.find(f => f.op === 'is')?.args).toEqual(['stripe_customer_id', null])
    expect(selectFilters.find(f => f.op === 'lt')?.args[0]).toBe('trial_ends_at')

    const byId = Object.fromEntries(rows.map(r => [r.user_id, r]))
    expect(byId.expired.tier).toBe('free')
    expect((byId.expired as Row & { downgraded_at?: string }).downgraded_at).toBeTruthy()
    expect(byId.active.tier).toBe('pro')
    expect(byId.paid.tier).toBe('pro')
    expect(byId.agency.tier).toBe('agency')
  })

  it('dry_run reports decisions and writes nothing', async () => {
    rows = [
      { user_id: 'expired', tier: 'pro', stripe_customer_id: null, trial_ends_at: past },
      { user_id: 'paying', tier: 'pro', stripe_customer_id: null, trial_ends_at: past },
    ]
    stripeState.customersByEmail['paying@example.com'] = ['cus_42']
    stripeState.activeCustomers.add('cus_42')

    const body = await (await GET(request('?dry_run=1'))).json()
    expect(body.dry_run).toBe(true)
    expect(body.candidates).toEqual([
      { user_id: 'expired', action: 'downgrade' },
      { user_id: 'paying', action: 'backfill', stripe_customer_id: 'cus_42' },
    ])
    expect(updates).toHaveLength(0)
    expect(rows.every(r => r.tier === 'pro' && r.stripe_customer_id === null)).toBe(true)
  })

  it('backfills stripe_customer_id instead of downgrading when Stripe has an active subscription', async () => {
    rows = [{ user_id: 'paying', tier: 'pro', stripe_customer_id: null, trial_ends_at: past }]
    stripeState.customersByEmail['paying@example.com'] = ['cus_old', 'cus_new']
    stripeState.activeCustomers.add('cus_new')

    const body = await (await GET(request())).json()
    expect(body).toEqual({ downgraded: 0, backfilled: 1, errors: 0 })
    expect(rows[0].tier).toBe('pro')
    expect(rows[0].stripe_customer_id).toBe('cus_new')
    expect(updates).toHaveLength(1)
    expect(updates[0].payload).not.toHaveProperty('tier')
  })

  it('a Stripe customer with no active subscription still gets downgraded', async () => {
    rows = [{ user_id: 'churned', tier: 'pro', stripe_customer_id: null, trial_ends_at: past }]
    stripeState.customersByEmail['churned@example.com'] = ['cus_x']
    const body = await (await GET(request())).json()
    expect(body).toEqual({ downgraded: 1, backfilled: 0, errors: 0 })
    expect(rows[0].tier).toBe('free')
    expect(rows[0].stripe_customer_id).toBeNull()
  })
})
