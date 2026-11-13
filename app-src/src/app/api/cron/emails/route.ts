import { NextRequest, NextResponse } from 'next/server'
import { clerkClient } from '@clerk/nextjs/server'
import { createClient } from '@/lib/supabase/server'
import { cronAuthError } from '@/lib/cron'
import { TRIAL_DAYS } from '@/lib/tier'
import { LIFECYCLE_TEMPLATES, dueTemplates, sendEmail } from '@/lib/email'

const DAY_MS = 86_400_000

type TierRow = { user_id: string; tier: string; trial_ends_at: string | null }

/**
 * Daily: send trial lifecycle emails (day 35 / 45 / 50 after trial start).
 * Each (user, template) pair is sent at most once, tracked in emails_sent.
 * A failure for one user is logged and never aborts the run.
 */
export async function GET(req: NextRequest) {
  const denied = cronAuthError(req)
  if (denied) return denied

  const supabase = createClient()
  const now = Date.now()

  const { data: rows, error: rowsError } = await supabase
    .from('user_tiers')
    .select('user_id, tier, trial_ends_at')
    .not('trial_ends_at', 'is', null)
  if (rowsError) {
    console.error('cron/emails user_tiers query error:', rowsError)
    return NextResponse.json({ error: 'db' }, { status: 500 })
  }

  const { data: sentRows, error: sentError } = await supabase
    .from('emails_sent')
    .select('user_id, template')
  if (sentError) {
    console.error('cron/emails emails_sent query error:', sentError)
    return NextResponse.json({ error: 'db' }, { status: 500 })
  }
  const alreadySent = new Set(
    (sentRows || []).map((r: { user_id: string; template: string }) => `${r.user_id}:${r.template}`)
  )

  let sent = 0
  let skipped = 0
  let errors = 0

  for (const row of (rows || []) as TierRow[]) {
    if (!row.trial_ends_at) continue
    const trialStart = new Date(row.trial_ends_at).getTime() - TRIAL_DAYS * DAY_MS
    const daysSinceStart = Math.floor((now - trialStart) / DAY_MS)

    const pending = dueTemplates(daysSinceStart, row.tier).filter(t => {
      const dup = alreadySent.has(`${row.user_id}:${t}`)
      if (dup) skipped++
      return !dup
    })
    if (pending.length === 0) continue

    let email: string | null = null
    try {
      const client = await clerkClient()
      const user = await client.users.getUser(row.user_id)
      email = user.primaryEmailAddress?.emailAddress ?? null
    } catch (err) {
      console.error(`cron/emails clerk lookup failed for ${row.user_id}:`, err)
      errors += pending.length
      continue
    }
    if (!email) {
      console.error(`cron/emails no primary email for ${row.user_id}`)
      errors += pending.length
      continue
    }

    for (const t of pending) {
      try {
        await sendEmail(email, LIFECYCLE_TEMPLATES[t]())
        const { error: insertError } = await supabase
          .from('emails_sent')
          .insert({ user_id: row.user_id, template: t })
        if (insertError) {
          // Sent but not recorded: surface loudly so a duplicate tomorrow is explainable.
          console.error(`cron/emails emails_sent insert failed for ${row.user_id}/${t}:`, insertError)
          errors++
        } else {
          alreadySent.add(`${row.user_id}:${t}`)
          sent++
        }
      } catch (err) {
        console.error(`cron/emails send failed for ${row.user_id}/${t}:`, err)
        errors++
      }
    }
  }

  return NextResponse.json({ sent, skipped, errors })
}
