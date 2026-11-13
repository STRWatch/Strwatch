import { describe, it, expect, vi, beforeEach } from 'vitest'

const DAY = 86_400_000
const TRIAL_DAYS = 45

// ---- supabase mock -------------------------------------------------------
let tierRows: { user_id: string; tier: string; trial_ends_at: string | null; founding_member?: boolean }[] = []
let sentRows: { user_id: string; template: string }[] = []
// Set to make the emails_sent insert fail (simulates a DB error on claim).
let claimError: { message: string } | null = null

function makeBuilder(table: string) {
  const b: Record<string, unknown> = {}
  const chain = () => b
  let pending: Promise<unknown> | null = null
  let rangeFrom = 0
  let rangeTo = Infinity
  const filters: Record<string, string> = {}

  b.select = vi.fn(() => (pending ? b : b))
  b.not = vi.fn(chain)
  b.lt = vi.fn(chain)
  b.order = vi.fn(chain)
  b.range = vi.fn((from: number, to: number) => { rangeFrom = from; rangeTo = to; return b })
  b.eq = vi.fn((col: string, val: string) => { filters[col] = val; return b })
  b.upsert = vi.fn((row: { user_id: string; template: string }) => {
    pending = (async () => {
      if (claimError) return { data: null, error: claimError }
      if (sentRows.some(r => r.user_id === row.user_id && r.template === row.template)) {
        return { data: [], error: null } // ignoreDuplicates: nothing inserted
      }
      sentRows.push(row)
      return { data: [{ template: row.template }], error: null }
    })()
    return b
  })
  b.delete = vi.fn(() => {
    pending = Promise.resolve().then(() => {
      sentRows = sentRows.filter(r => !(r.user_id === filters.user_id && r.template === filters.template))
      return { error: null }
    })
    return b
  })
  const resolve = () => {
    if (pending) return pending
    if (table === 'user_tiers') {
      return Promise.resolve({ data: tierRows.slice(rangeFrom, rangeTo + 1), error: null })
    }
    return Promise.resolve({ data: [], error: null })
  }
  b.then = (onOk: (v: unknown) => unknown, onErr?: (e: unknown) => unknown) =>
    resolve().then(onOk, onErr)
  return b
}

vi.mock('@/lib/supabase/server', () => ({
  createClient: () => ({ from: (table: string) => makeBuilder(table) }),
}))

// ---- clerk mock ----------------------------------------------------------
vi.mock('@clerk/nextjs/server', () => ({
  clerkClient: async () => ({
    users: {
      getUser: async (id: string) => ({
        primaryEmailAddress: { emailAddress: `${id}@example.com` },
      }),
    },
  }),
}))

// ---- email mock ----------------------------------------------------------
const { sendEmail } = vi.hoisted(() => ({
  sendEmail: vi.fn(async (_to: string, _email: { subject: string }): Promise<void> => {}),
}))
vi.mock('@/lib/email', async importOriginal => {
  const actual = await importOriginal<typeof import('@/lib/email')>()
  return { ...actual, sendEmail }
})

import { GET } from '@/app/api/cron/emails/route'

function trialEndsAtForDaysSinceStart(days: number): string {
  // trial start = now - days; trial_ends_at = start + 45d. Add an hour of slack
  // so floor() does not flip the day boundary.
  return new Date(Date.now() - days * DAY + TRIAL_DAYS * DAY + 3_600_000).toISOString()
}

function request() {
  return new Request('http://localhost/api/cron/emails', {
    headers: { authorization: 'Bearer test-secret' },
  }) as never
}

beforeEach(() => {
  tierRows = []
  sentRows = []
  claimError = null
  sendEmail.mockClear()
  process.env.CRON_SECRET = 'test-secret'
})

describe('GET /api/cron/emails', () => {
  it('rejects without the cron secret', async () => {
    const res = await GET(new Request('http://localhost/api/cron/emails') as never)
    expect(res.status).toBe(401)
    expect(sendEmail).not.toHaveBeenCalled()
  })

  it('500s when CRON_SECRET is unset', async () => {
    delete process.env.CRON_SECRET
    const res = await GET(request())
    expect(res.status).toBe(500)
  })

  it('sends day35 once and never again on later runs', async () => {
    tierRows = [{ user_id: 'u1', tier: 'pro', trial_ends_at: trialEndsAtForDaysSinceStart(36) }]

    const first = await (await GET(request())).json()
    expect(first).toEqual({ sent: 1, skipped: 0, errors: 0 })
    expect(sendEmail).toHaveBeenCalledTimes(1)
    expect(sendEmail.mock.calls[0][0]).toBe('u1@example.com')

    const second = await (await GET(request())).json()
    expect(second).toEqual({ sent: 0, skipped: 1, errors: 0 })
    expect(sendEmail).toHaveBeenCalledTimes(1)
  })

  it('sends day45 and day50 only to free users, each exactly once across runs', async () => {
    tierRows = [
      { user_id: 'free', tier: 'free', trial_ends_at: trialEndsAtForDaysSinceStart(52) },
      { user_id: 'paid', tier: 'pro', trial_ends_at: trialEndsAtForDaysSinceStart(52) },
    ]

    const first = await (await GET(request())).json()
    // free: day35 + day45 + day50; paid: day35 only
    expect(first).toEqual({ sent: 4, skipped: 0, errors: 0 })
    expect(sentRows.map(r => `${r.user_id}:${r.template}`).sort()).toEqual([
      'free:day35', 'free:day45', 'free:day50', 'paid:day35',
    ])

    const second = await (await GET(request())).json()
    expect(second).toEqual({ sent: 0, skipped: 4, errors: 0 })
    expect(sendEmail).toHaveBeenCalledTimes(4)

    const subjects = sendEmail.mock.calls.map(c => c[1].subject)
    expect(new Set(subjects).size).toBe(3)
  })

  it('does not send anything before day 35', async () => {
    tierRows = [{ user_id: 'u1', tier: 'pro', trial_ends_at: trialEndsAtForDaysSinceStart(20) }]
    const body = await (await GET(request())).json()
    expect(body).toEqual({ sent: 0, skipped: 0, errors: 0 })
    expect(sendEmail).not.toHaveBeenCalled()
  })

  it('send failure deletes the claimed row so it retries next run', async () => {
    tierRows = [{ user_id: 'u1', tier: 'pro', trial_ends_at: trialEndsAtForDaysSinceStart(36) }]
    sendEmail.mockRejectedValueOnce(new Error('resend down'))

    const first = await (await GET(request())).json()
    expect(first).toEqual({ sent: 0, skipped: 0, errors: 1 })
    expect(sentRows).toHaveLength(0)
    expect(sendEmail).toHaveBeenCalledTimes(1)

    const second = await (await GET(request())).json()
    expect(second).toEqual({ sent: 1, skipped: 0, errors: 0 })
    expect(sendEmail).toHaveBeenCalledTimes(2)
    expect(sentRows).toEqual([{ user_id: 'u1', template: 'day35' }])
  })

  it('insert wins then sends: the emails_sent row exists before sendEmail is called', async () => {
    tierRows = [{ user_id: 'u1', tier: 'pro', trial_ends_at: trialEndsAtForDaysSinceStart(36) }]
    let rowsAtSendTime: typeof sentRows = []
    sendEmail.mockImplementationOnce(async () => { rowsAtSendTime = [...sentRows] })

    const body = await (await GET(request())).json()
    expect(body).toEqual({ sent: 1, skipped: 0, errors: 0 })
    expect(rowsAtSendTime).toEqual([{ user_id: 'u1', template: 'day35' }])
  })

  it('a pre-existing emails_sent row means no send (another run already claimed it)', async () => {
    tierRows = [{ user_id: 'u1', tier: 'pro', trial_ends_at: trialEndsAtForDaysSinceStart(36) }]
    sentRows = [{ user_id: 'u1', template: 'day35' }]
    const body = await (await GET(request())).json()
    expect(body).toEqual({ sent: 0, skipped: 1, errors: 0 })
    expect(sendEmail).not.toHaveBeenCalled()
  })

  it('a claim DB error is counted and does not send', async () => {
    tierRows = [{ user_id: 'u1', tier: 'pro', trial_ends_at: trialEndsAtForDaysSinceStart(36) }]
    claimError = { message: 'db down' }
    const body = await (await GET(request())).json()
    expect(body).toEqual({ sent: 0, skipped: 0, errors: 1 })
    expect(sendEmail).not.toHaveBeenCalled()
  })

  it('paginates user_tiers in pages of 500', async () => {
    tierRows = Array.from({ length: 1203 }, (_, i) => ({
      user_id: `u${String(i).padStart(4, '0')}`, tier: 'pro', trial_ends_at: trialEndsAtForDaysSinceStart(36),
    }))
    const body = await (await GET(request())).json()
    expect(body).toEqual({ sent: 1203, skipped: 0, errors: 0 })
  })
})
