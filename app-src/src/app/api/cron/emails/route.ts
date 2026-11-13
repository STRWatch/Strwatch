import { NextRequest, NextResponse } from 'next/server'
import { clerkClient } from '@clerk/nextjs/server'
import { createClient } from '@/lib/supabase/server'
import { cronAuthError } from '@/lib/cron'
import { TRIAL_DAYS } from '@/lib/tier'
import { LIFECYCLE_TEMPLATES, dueTemplates, sendEmail, type LifecycleTemplate } from '@/lib/email'

const DAY_MS = 86_400_000
const PAGE_SIZE = 500

type TierRow = {
  user_id: string
  tier: string
  trial_ends_at: string | null
  founding_member: boolean | null
}

/**
 * Daily: send trial lifecycle emails (day 35 / 45 / 50 after trial start).
 *
 * The emails_sent unique(user_id, template) row is the lock: we insert first
 * with ignoreDuplicates, and only send when our insert won. A failed send
 * deletes the row so tomorrow's run retries. A failure for one user is logged
 * and never aborts the run.
 */
export async function GET(req: NextRequest) {
  const denied = cronAuthError(req)
  if (denied) return denied

  const supabase = createClient()
  const now = Date.now()
  // Day 35 is reached when trial_ends_at is within 10 days; anything later is not due yet.
  const dueCutoff = new Date(now + (TRIAL_DAYS - 35) * DAY_MS).toISOString()

  let sent = 0
  let skipped = 0
  let errors = 0

  for (let from = 0; ; from += PAGE_SIZE) {
    const { data: rows, error: rowsError } = await supabase
      .from('user_tiers')
      .select('user_id, tier, trial_ends_at, founding_member')
      .not('trial_ends_at', 'is', null)
      .lt('trial_ends_at', dueCutoff)
      .order('user_id', { ascending: true })
      .range(from, from + PAGE_SIZE - 1)
    if (rowsError) {
      console.error('cron/emails user_tiers query error:', rowsError)
      return NextResponse.json({ error: 'db', sent, skipped, errors }, { status: 500 })
    }
    const page = (rows || []) as TierRow[]
    if (page.length === 0) break

    for (const row of page) {
      if (!row.trial_ends_at) continue
      const trialStart = new Date(row.trial_ends_at).getTime() - TRIAL_DAYS * DAY_MS
      const daysSinceStart = Math.floor((now - trialStart) / DAY_MS)
      const due = dueTemplates(daysSinceStart, row.tier)
      if (due.length === 0) continue

      // Claim each (user, template) in the DB before doing any work.
      const claimed: LifecycleTemplate[] = []
      for (const t of due) {
        // ON CONFLICT DO NOTHING + RETURNING: an empty result means another run already holds it.
        const { data: inserted, error: insertError } = await supabase
          .from('emails_sent')
          .upsert(
            { user_id: row.user_id, template: t },
            { onConflict: 'user_id,template', ignoreDuplicates: true }
          )
          .select('template')
        if (insertError) {
          console.error(`cron/emails claim failed for ${row.user_id}/${t}:`, insertError)
          errors++
          continue
        }
        if (!inserted || inserted.length === 0) {
          skipped++
          continue
        }
        claimed.push(t)
      }
      if (claimed.length === 0) continue

      const release = async (t: LifecycleTemplate) => {
        const { error } = await supabase
          .from('emails_sent')
          .delete()
          .eq('user_id', row.user_id)
          .eq('template', t)
        if (error) console.error(`cron/emails release failed for ${row.user_id}/${t}:`, error)
      }

      let email: string | null = null
      try {
        const client = await clerkClient()
        const user = await client.users.getUser(row.user_id)
        email = user.primaryEmailAddress?.emailAddress ?? null
      } catch (err) {
        console.error(`cron/emails clerk lookup failed for ${row.user_id}:`, err)
      }
      if (!email) {
        console.error(`cron/emails no primary email for ${row.user_id}`)
        for (const t of claimed) await release(t)
        errors += claimed.length
        continue
      }

      for (const t of claimed) {
        try {
          await sendEmail(email, LIFECYCLE_TEMPLATES[t]({ foundingMember: !!row.founding_member }))
          sent++
        } catch (err) {
          console.error(`cron/emails send failed for ${row.user_id}/${t}:`, err)
          await release(t)
          errors++
        }
      }
    }

    if (page.length < PAGE_SIZE) break
  }

  return NextResponse.json({ sent, skipped, errors })
}
