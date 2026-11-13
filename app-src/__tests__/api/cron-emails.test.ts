import { describe, it, expect, vi, beforeEach } from 'vitest'

const DAY = 86_400_000
const TRIAL_DAYS = 45

// ---- supabase mock -------------------------------------------------------
let tierRows: { user_id: string; tier: string; trial_ends_at: string | null }[] = []
let sentRows: { user_id: string; template: string }[] = []

function makeBuilder(table: string) {
  const b: Record<string, unknown> = {}
  const chain = () => b
  const resolve = () => {
    if (table === 'user_tiers') return Promise.resolve({ data: tierRows, error: null })
    if (table === 'emails_sent') return Promise.resolve({ data: sentRows, error: null })
    return Promise.resolve({ data: [], error: null })
  }
  b.select = vi.fn(chain)
  b.not = vi.fn(chain)
  b.insert = vi.fn((row: { user_id: string; template: string }) => {
    if (sentRows.some(r => r.user_id === row.user_id && r.template === row.template)) {
      return Promise.resolve({ error: { message: 'duplicate key' } })
    }
    sentRows.push(row)
    return Promise.resolve({ error: null })
  })
  // The builder is awaited directly after select().not(); make it thenable.
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

  it('counts a failed send as an error and does not record it, so it retries next run', async () => {
    tierRows = [{ user_id: 'u1', tier: 'pro', trial_ends_at: trialEndsAtForDaysSinceStart(36) }]
    sendEmail.mockRejectedValueOnce(new Error('resend down'))

    const first = await (await GET(request())).json()
    expect(first).toEqual({ sent: 0, skipped: 0, errors: 1 })
    expect(sentRows).toHaveLength(0)

    const second = await (await GET(request())).json()
    expect(second).toEqual({ sent: 1, skipped: 0, errors: 0 })
    expect(sendEmail).toHaveBeenCalledTimes(2)
  })
})
