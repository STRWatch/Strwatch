import { NextRequest, NextResponse } from 'next/server'
import Stripe from 'stripe'
import { createClient } from '@/lib/supabase/server'

function requireEnv(name: string): string {
  const value = process.env[name]
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`)
  }
  return value
}

/**
 * Stripe client and webhook secret, read inside the handler rather than at
 * module load. `new Stripe(undefined)` throws, and `next build` evaluates this
 * module while collecting page data, so a module-level client fails the build
 * whenever STRIPE_SECRET_KEY is absent from the build environment.
 */
function getStripeWebhookEnv(): { stripe: Stripe; webhookSecret: string } {
  const secretKey = requireEnv('STRIPE_SECRET_KEY')
  const webhookSecret = requireEnv('STRIPE_WEBHOOK_SECRET')
  return {
    stripe: new Stripe(secretKey, { apiVersion: '2026-02-25.clover' }),
    webhookSecret,
  }
}

function customerId(value: unknown): string | null {
  if (typeof value === 'string') return value
  if (value && typeof value === 'object' && typeof (value as { id?: unknown }).id === 'string') {
    return (value as { id: string }).id
  }
  return null
}

export async function POST(req: NextRequest) {
  const { stripe, webhookSecret } = getStripeWebhookEnv()
  const body = await req.text()
  const sig = req.headers.get('stripe-signature')!
  let event: Stripe.Event
  try {
    event = stripe.webhooks.constructEvent(body, sig, webhookSecret)
  } catch (err) {
    return NextResponse.json({ error: 'Invalid signature' }, { status: 400 })
  }
  const supabase = createClient()
  if (event.type === 'checkout.session.completed') {
    const session = event.data.object as any
    const userId = session.metadata?.userId
    const tier = session.metadata?.tier
    if (userId && tier) {
      // Clear trial_ends_at so user is recognized as paid, not trial.
      // Persist the Stripe customer so later webhooks can be resolved without metadata.
      const { error } = await supabase.from('user_tiers').upsert(
        {
          user_id: userId,
          tier,
          trial_ends_at: null,
          stripe_customer_id: customerId(session.customer),
          updated_at: new Date().toISOString(),
        },
        { onConflict: 'user_id' }
      )
      if (error) {
        // Non-2xx makes Stripe retry; the upsert is idempotent so retries are safe.
        console.error('webhook checkout.session.completed upsert error:', error)
        return NextResponse.json({ error: 'db' }, { status: 500 })
      }
    }
  }
  if (event.type === 'customer.subscription.deleted') {
    const sub = event.data.object as any
    let userId: string | null = sub.metadata?.userId || null
    if (!userId) {
      // Subscriptions created before subscription_data.metadata was set: resolve by customer
      const stripeCustomerId = customerId(sub.customer)
      if (stripeCustomerId) {
        const { data, error } = await supabase
          .from('user_tiers')
          .select('user_id')
          .eq('stripe_customer_id', stripeCustomerId)
          .maybeSingle()
        if (error) {
          console.error('webhook customer lookup error:', error)
          return NextResponse.json({ error: 'db' }, { status: 500 })
        }
        userId = data?.user_id ?? null
      }
    }
    if (userId) {
      const { error } = await supabase.from('user_tiers').upsert(
        { user_id: userId, tier: 'free', trial_ends_at: null, updated_at: new Date().toISOString() },
        { onConflict: 'user_id' }
      )
      if (error) {
        console.error('webhook customer.subscription.deleted upsert error:', error)
        return NextResponse.json({ error: 'db' }, { status: 500 })
      }
    }
  }
  return NextResponse.json({ received: true })
}
