import { NextRequest, NextResponse } from 'next/server'
import Stripe from 'stripe'
import { createClient } from '@/lib/supabase/server'

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, { apiVersion: '2026-02-25.clover' })

function customerId(value: unknown): string | null {
  if (typeof value === 'string') return value
  if (value && typeof value === 'object' && typeof (value as { id?: unknown }).id === 'string') {
    return (value as { id: string }).id
  }
  return null
}

export async function POST(req: NextRequest) {
  const body = await req.text()
  const sig = req.headers.get('stripe-signature')!
  let event: Stripe.Event
  try {
    event = stripe.webhooks.constructEvent(body, sig, process.env.STRIPE_WEBHOOK_SECRET!)
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
      await supabase.from('user_tiers').upsert(
        {
          user_id: userId,
          tier,
          trial_ends_at: null,
          stripe_customer_id: customerId(session.customer),
          updated_at: new Date().toISOString(),
        },
        { onConflict: 'user_id' }
      )
    }
  }
  if (event.type === 'customer.subscription.deleted') {
    const sub = event.data.object as any
    let userId: string | null = sub.metadata?.userId || null
    if (!userId) {
      // Subscriptions created before subscription_data.metadata was set: resolve by customer
      const stripeCustomerId = customerId(sub.customer)
      if (stripeCustomerId) {
        const { data } = await supabase
          .from('user_tiers')
          .select('user_id')
          .eq('stripe_customer_id', stripeCustomerId)
          .maybeSingle()
        userId = data?.user_id ?? null
      }
    }
    if (userId) {
      await supabase.from('user_tiers').upsert(
        { user_id: userId, tier: 'free', trial_ends_at: null, updated_at: new Date().toISOString() },
        { onConflict: 'user_id' }
      )
    }
  }
  return NextResponse.json({ received: true })
}
