import { NextRequest, NextResponse } from 'next/server'
import { clerkClient } from '@clerk/nextjs/server'
import { createClient } from '@/lib/supabase/server'
import { cronAuthError } from '@/lib/cron'
import { getStripe } from '@/lib/stripe'

const PAGE_SIZE = 500

type Candidate = { user_id: string; trial_ends_at: string | null }
type Action = 'downgrade' | 'backfill' | 'skip'
type Decision = { user_id: string; action: Action; stripe_customer_id?: string; reason?: string }

/** Escape a value for a Stripe search query string literal. */
function stripeQuote(value: string): string {
  return value.replace(/\\/g, '\\\\').replace(/'/g, "\\'")
}

/**
 * A lapsed trial row with no stripe_customer_id might still be paying (e.g.
 * a webhook that never landed). Look the user up in Stripe by email; if any
 * customer with that email has an active subscription, return its id.
 */
async function findActiveStripeCustomer(email: string): Promise<string | null> {
  const stripe = getStripe()
  const customers = await stripe.customers.search({ query: `email:'${stripeQuote(email)}'`, limit: 10 })
  for (const customer of customers.data) {
    const subs = await stripe.subscriptions.list({ customer: customer.id, status: 'active', limit: 1 })
    if (subs.data.length > 0) return customer.id
  }
  return null
}

async function decide(userId: string): Promise<Decision> {
  let email: string | null = null
  try {
    const client = await clerkClient()
    const user = await client.users.getUser(userId)
    email = user.primaryEmailAddress?.emailAddress ?? null
  } catch (err) {
    console.error(`cron/tiers clerk lookup failed for ${userId}:`, err)
    return { user_id: userId, action: 'skip', reason: 'clerk_lookup_failed' }
  }
  if (!email) {
    // Cannot verify against Stripe without an email; downgrade is still the correct default.
    return { user_id: userId, action: 'downgrade', reason: 'no_email' }
  }
  try {
    const customerId = await findActiveStripeCustomer(email)
    if (customerId) return { user_id: userId, action: 'backfill', stripe_customer_id: customerId }
    return { user_id: userId, action: 'downgrade' }
  } catch (err) {
    // Stripe unreachable: do not downgrade on a guess; retry tomorrow.
    console.error(`cron/tiers stripe check failed for ${userId}:`, err)
    return { user_id: userId, action: 'skip', reason: 'stripe_check_failed' }
  }
}

/**
 * Daily: downgrade expired, unpaid Pro trials to Free.
 * A row is a candidate when tier != 'free', stripe_customer_id is null, and
 * trial_ends_at is in the past. Before downgrading, Stripe is checked by
 * email; a found active subscription backfills stripe_customer_id instead.
 *
 * `?dry_run=1` returns the per-user decisions and writes nothing.
 */
export async function GET(req: NextRequest) {
  const denied = cronAuthError(req)
  if (denied) return denied

  const dryRun = req.nextUrl.searchParams.get('dry_run') === '1'
  const supabase = createClient()
  const nowIso = new Date().toISOString()

  const candidates: Candidate[] = []
  for (let from = 0; ; from += PAGE_SIZE) {
    const { data, error } = await supabase
      .from('user_tiers')
      .select('user_id, trial_ends_at')
      .neq('tier', 'free')
      .is('stripe_customer_id', null)
      .lt('trial_ends_at', nowIso)
      .order('user_id', { ascending: true })
      .range(from, from + PAGE_SIZE - 1)
    if (error) {
      console.error('cron/tiers candidate query error:', error)
      return NextResponse.json({ error: 'db' }, { status: 500 })
    }
    const page = (data || []) as Candidate[]
    candidates.push(...page)
    if (page.length < PAGE_SIZE) break
  }

  const decisions: Decision[] = []
  for (const c of candidates) decisions.push(await decide(c.user_id))

  if (dryRun) {
    return NextResponse.json({ dry_run: true, candidates: decisions })
  }

  let downgraded = 0
  let backfilled = 0
  let errors = 0
  for (const d of decisions) {
    if (d.action === 'skip') {
      errors++
      continue
    }
    if (d.action === 'backfill') {
      console.warn(`cron/tiers: ${d.user_id} has active Stripe subscription ${d.stripe_customer_id}; backfilling instead of downgrading`)
      const { error } = await supabase
        .from('user_tiers')
        .update({ stripe_customer_id: d.stripe_customer_id, updated_at: nowIso })
        .eq('user_id', d.user_id)
        .is('stripe_customer_id', null)
      if (error) {
        console.error(`cron/tiers backfill failed for ${d.user_id}:`, error)
        errors++
      } else {
        backfilled++
      }
      continue
    }
    const { error } = await supabase
      .from('user_tiers')
      .update({ tier: 'free', downgraded_at: nowIso, updated_at: nowIso })
      .eq('user_id', d.user_id)
      .neq('tier', 'free')
      .is('stripe_customer_id', null)
    if (error) {
      console.error(`cron/tiers downgrade failed for ${d.user_id}:`, error)
      errors++
    } else {
      downgraded++
    }
  }

  return NextResponse.json({ downgraded, backfilled, errors })
}
