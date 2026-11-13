import { describe, it, expect, vi, beforeEach } from 'vitest'

const { state } = vi.hoisted(() => ({
  // The route reads ANTHROPIC_API_KEY at module load; set it before the import.
  _env: (process.env.ANTHROPIC_API_KEY = 'sk-ant-test'),
  state: { userId: 'user_1' as string | null, todayCount: 0, tier: { isTrialActive: true, isPaid: false, isAgency: false } },
}))

vi.mock('@clerk/nextjs/server', () => ({ auth: async () => ({ userId: state.userId }) }))
vi.mock('@/lib/tier', () => ({ getEffectiveTier: async () => ({ tier: 'pro', trialEndsAt: null, ...state.tier }) }))

const countCall = vi.fn()
vi.mock('@/lib/supabase/server', () => ({
  createClient: () => ({
    from: () => {
      const b: Record<string, unknown> = {}
      const chain = () => b
      b.select = vi.fn((_cols: string, opts?: { count?: string; head?: boolean }) => { countCall(opts); return b })
      b.eq = vi.fn(chain)
      b.gte = vi.fn(chain)
      b.insert = vi.fn(chain)
      b.single = vi.fn(() => Promise.resolve({ data: { id: 'scan_1' }, error: null }))
      b.then = (ok: (v: unknown) => unknown, err?: (e: unknown) => unknown) =>
        Promise.resolve({ count: state.todayCount, error: null }).then(ok, err)
      return b
    },
  }),
}))

import { POST } from '@/app/api/scans/generate/route'
import { NextRequest } from 'next/server'

function request(city = 'Austin, TX') {
  return new NextRequest('http://localhost/api/scans/generate', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ city }),
  })
}

const fetchSpy = vi.fn()

beforeEach(() => {
  state.userId = 'user_1'
  state.todayCount = 0
  state.tier = { isTrialActive: true, isPaid: false, isAgency: false }
  fetchSpy.mockReset()
  vi.stubGlobal('fetch', fetchSpy)
})

describe('POST /api/scans/generate daily cap', () => {
  it('returns 429 for a trial user at 10 scans today and never calls Anthropic', async () => {
    state.todayCount = 10
    const res = await POST(request())
    expect(res.status).toBe(429)
    const body = await res.json()
    expect(body.error).toMatch(/10 per day/)
    expect(fetchSpy).not.toHaveBeenCalled()
    expect(countCall).toHaveBeenCalledWith({ count: 'exact', head: true })
  })

  it('paid users get a 50 cap: 10 scans is fine, 50 is not', async () => {
    state.tier = { isTrialActive: false, isPaid: true, isAgency: false }
    state.todayCount = 50
    expect((await POST(request())).status).toBe(429)

    state.todayCount = 10
    // Below the cap: the route proceeds to Anthropic (which is stubbed to fail fast here).
    fetchSpy.mockResolvedValueOnce({ ok: false, status: 500, text: async () => 'stub' })
    const res = await POST(request())
    expect(res.status).not.toBe(429)
    expect(fetchSpy).toHaveBeenCalledTimes(1)
  })

  it('401 when unauthenticated', async () => {
    state.userId = null
    expect((await POST(request())).status).toBe(401)
  })
})
