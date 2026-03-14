import { NextRequest, NextResponse } from 'next/server'
import Stripe from 'stripe'
import { createClient } from '@/lib/supabase/server'

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, { apiVersion: '2024-12-18.acacia' })

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
    const session = event.data.object as Stripe.CheckoutSession
    const userId = session.metadata?.userId
    const tier = session.metadata?.tier
    if (userId && tier) {
      await supabase.from('user_tiers').upsert(
        { user_id: userId, tier, updated_at: new Date().toISOString() },
        { onConflict: 'user_id' }
      )
    }
  }
  if (event.type === 'customer.subscription.deleted') {
    const sub = event.data.object as Stripe.Subscription
    const userId = sub.metadata?.userId
    if (userId) {
      await supabase.from('user_tiers').upsert(
        { user_id: userId, tier: 'free', updated_at: new Date().toISOString() },
        { onConflict: 'user_id' }
      )
    }
  }
  return NextResponse.json({ received: true })
}
