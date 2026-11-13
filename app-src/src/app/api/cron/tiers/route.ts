import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { cronAuthError } from '@/lib/cron'

/**
 * Daily: downgrade expired, unpaid Pro trials to Free.
 * A row is a lapsed trial when tier != 'free', there is no Stripe customer
 * (checkout nulls trial_ends_at and sets stripe_customer_id), and
 * trial_ends_at is in the past.
 */
export async function GET(req: NextRequest) {
  const denied = cronAuthError(req)
  if (denied) return denied

  const supabase = createClient()
  const nowIso = new Date().toISOString()

  const { data, error } = await supabase
    .from('user_tiers')
    .update({ tier: 'free', downgraded_at: nowIso, updated_at: nowIso })
    .neq('tier', 'free')
    .is('stripe_customer_id', null)
    .lt('trial_ends_at', nowIso)
    .select('user_id')

  if (error) {
    console.error('cron/tiers downgrade error:', error)
    return NextResponse.json({ error: 'db' }, { status: 500 })
  }

  return NextResponse.json({ downgraded: data?.length ?? 0 })
}
