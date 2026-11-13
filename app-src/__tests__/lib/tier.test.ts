import { describe, it, expect, vi, beforeEach } from 'vitest'

// Chainable fake of the supabase query builder. `tables` maps table name ->
// the row returned by .single(). Every write call is recorded for assertions.
const calls: { op: string; table: string; payload?: unknown }[] = []
let tableRows: Record<string, unknown> = {}

function makeBuilder(table: string) {
  const b: Record<string, unknown> = {}
  const chain = () => b
  b.upsert = vi.fn((payload: unknown) => {
    calls.push({ op: 'upsert', table, payload })
    return Promise.resolve({ error: null })
  })
  b.update = vi.fn((payload: unknown) => {
    calls.push({ op: 'update', table, payload })
    return b
  })
  b.select = vi.fn(chain)
  b.eq = vi.fn(chain)
  b.single = vi.fn(() => Promise.resolve({ data: tableRows[table] ?? null, error: null }))
  return b
}

vi.mock('@/lib/supabase/server', () => ({
  createClient: () => ({ from: (table: string) => makeBuilder(table) }),
}))

import { getEffectiveTier, TRIAL_DAYS } from '@/lib/tier'

const DAY = 86_400_000
const future = (days: number) => new Date(Date.now() + days * DAY).toISOString()
const past = (days: number) => new Date(Date.now() - days * DAY).toISOString()

beforeEach(() => {
  calls.length = 0
  tableRows = {}
})

describe('getEffectiveTier', () => {
  it('bootstraps a 45-day pro trial row with ignoreDuplicates', async () => {
    tableRows.user_tiers = { tier: 'pro', trial_ends_at: future(45) }
    await getEffectiveTier('user_1')
    const upsert = calls.find(c => c.op === 'upsert')
    expect(upsert).toBeDefined()
    const payload = upsert!.payload as { tier: string; trial_ends_at: string }
    expect(payload.tier).toBe('pro')
    const diffDays = (new Date(payload.trial_ends_at).getTime() - Date.now()) / DAY
    expect(Math.round(diffDays)).toBe(TRIAL_DAYS)
  })

  it('active trial: tier pro, trial active, not paid', async () => {
    tableRows.user_tiers = { tier: 'pro', trial_ends_at: future(10) }
    const t = await getEffectiveTier('user_1')
    expect(t.tier).toBe('pro')
    expect(t.isTrialActive).toBe(true)
    expect(t.isPaid).toBe(false)
    expect(t.isAgency).toBe(false)
    expect(t.trialEndsAt).not.toBeNull()
  })

  it('expired trial: reads as free without writing a downgrade', async () => {
    tableRows.user_tiers = { tier: 'pro', trial_ends_at: past(2) }
    const t = await getEffectiveTier('user_1')
    expect(t.tier).toBe('free')
    expect(t.isTrialActive).toBe(false)
    expect(t.isPaid).toBe(false)
    expect(t.trialEndsAt).not.toBeNull()
    expect(calls.filter(c => c.op === 'update')).toHaveLength(0)
  })

  it('paid pro: trial_ends_at null, isPaid true', async () => {
    tableRows.user_tiers = { tier: 'pro', trial_ends_at: null }
    const t = await getEffectiveTier('user_1')
    expect(t.tier).toBe('pro')
    expect(t.isTrialActive).toBe(false)
    expect(t.isPaid).toBe(true)
    expect(t.isAgency).toBe(false)
    expect(t.trialEndsAt).toBeNull()
  })

  it('agency: isAgency and isPaid true regardless of trial_ends_at', async () => {
    tableRows.user_tiers = { tier: 'agency', trial_ends_at: past(1) }
    const t = await getEffectiveTier('user_1')
    expect(t.tier).toBe('agency')
    expect(t.isAgency).toBe(true)
    expect(t.isPaid).toBe(true)
    expect(t.isTrialActive).toBe(false)
  })

  it('unknown tier value falls back to free', async () => {
    tableRows.user_tiers = { tier: 'enterprise', trial_ends_at: null }
    const t = await getEffectiveTier('user_1')
    expect(t.tier).toBe('free')
    expect(t.isPaid).toBe(false)
  })
})
