import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import Stripe from 'stripe'
import { createClient } from '@/lib/supabase/server'
import { appUrl } from '@/lib/url'

type StripeEnv = {
  secretKey: string
  priceIds: Record<string, string>
}

/**
 * Reads the Stripe configuration from the environment, throwing an error that
 * names the first missing variable. Called inside the handler (not at module
 * load) so a misconfigured deployment fails on the request with a clear message
 * instead of crashing at import with a cryptic 500.
 */
function getStripeEnv(): StripeEnv {
  const required = ['STRIPE_SECRET_KEY', 'STRIPE_PRICE_PRO', 'STRIPE_PRICE_AGENCY', 'STRIPE_PRICE_FOUNDING'] as const
  const values: Partial<Record<(typeof required)[number], string>> = {}
  for (const name of required) {
    const value = process.env[name]
    if (!value) {
      throw new Error(`Missing required environment variable: ${name}`)
    }
    values[name] = value
  }
  return {
    secretKey: values.STRIPE_SECRET_KEY!,
    priceIds: {
      pro:      values.STRIPE_PRICE_PRO!,
      agency:   values.STRIPE_PRICE_AGENCY!,
      // Founding-member Pro ($19/mo locked). Grants tier 'pro'; gated on user_tiers.founding_member.
      founding: values.STRIPE_PRICE_FOUNDING!,
    },
  }
}

export async function POST(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  const { secretKey, priceIds } = getStripeEnv()
  const stripe = new Stripe(secretKey, { apiVersion: '2026-02-25.clover' })
  const { tier } = await req.json()
  const priceId = typeof tier === 'string' ? priceIds[tier] : undefined
  if (!priceId) return NextResponse.json({ error: 'Invalid tier' }, { status: 400 })

  const isFounding = tier === 'founding'
  if (isFounding) {
    const { data, error } = await createClient()
      .from('user_tiers')
      .select('founding_member')
      .eq('user_id', userId)
      .maybeSingle()
    if (error) {
      console.error('stripe/checkout founding lookup error:', error)
      return NextResponse.json({ error: 'db' }, { status: 500 })
    }
    if (!data?.founding_member) {
      return NextResponse.json({ error: 'Founding offer not available' }, { status: 403 })
    }
  }

  // The webhook reads metadata.tier to set user_tiers.tier; founding checkouts grant 'pro'.
  const metadata: Record<string, string> = isFounding
    ? { userId, tier: 'pro', founding: 'true' }
    : { userId, tier }
  const session = await stripe.checkout.sessions.create({
    mode: 'subscription',
    payment_method_types: ['card'],
    line_items: [{ price: priceId, quantity: 1 }],
    success_url: `${appUrl()}/dashboard?upgraded=true`,
    cancel_url: isFounding ? `${appUrl()}/dashboard/settings` : `${appUrl()}/dashboard/markets`,
    metadata,
    // Also stamp the Subscription itself so customer.subscription.* webhooks can resolve the user
    subscription_data: { metadata },
  })
  return NextResponse.json({ url: session.url })
}
