import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import Stripe from 'stripe'
import { createClient } from '@/lib/supabase/server'
import { appUrl } from '@/lib/url'
import { getEffectiveTier } from '@/lib/tier'

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
function requireEnv(name: string): string {
  const value = process.env[name]
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`)
  }
  return value
}

function getStripeEnv(tier: string): StripeEnv {
  const priceIds: Record<string, string> = {
    pro:    requireEnv('STRIPE_PRICE_PRO'),
    agency: requireEnv('STRIPE_PRICE_AGENCY'),
  }
  // Founding-member Pro ($19/mo locked). Grants tier 'pro'; gated on
  // user_tiers.founding_member. Only required when actually requested so a
  // deployment without the founding price still sells Pro/Agency.
  if (tier === 'founding') priceIds.founding = requireEnv('STRIPE_PRICE_FOUNDING')
  return { secretKey: requireEnv('STRIPE_SECRET_KEY'), priceIds }
}

export async function POST(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  const { tier } = await req.json()
  if (typeof tier !== 'string') return NextResponse.json({ error: 'Invalid tier' }, { status: 400 })
  const { secretKey, priceIds } = getStripeEnv(tier)
  const stripe = new Stripe(secretKey, { apiVersion: '2026-02-25.clover' })
  const priceId = priceIds[tier]
  if (!priceId) return NextResponse.json({ error: 'Invalid tier' }, { status: 400 })

  // Paying subscribers change plans in the billing portal. A second checkout
  // would mint a second subscription (and, without `customer`, a second Stripe
  // customer); cancelling either one would then downgrade the user.
  const { isPaid } = await getEffectiveTier(userId)
  if (isPaid) {
    return NextResponse.json({ error: 'use_billing_portal' }, { status: 409 })
  }

  const { data: row, error: rowError } = await createClient()
    .from('user_tiers')
    .select('founding_member, stripe_customer_id')
    .eq('user_id', userId)
    .maybeSingle()
  if (rowError) {
    console.error('stripe/checkout user_tiers lookup error:', rowError)
    return NextResponse.json({ error: 'db' }, { status: 500 })
  }

  const isFounding = tier === 'founding'
  if (isFounding && !row?.founding_member) {
    return NextResponse.json({ error: 'Founding offer not available' }, { status: 403 })
  }
  // Reuse the Stripe customer from an earlier subscription (e.g. a lapsed one)
  // instead of letting Checkout create another.
  const existingCustomer = typeof row?.stripe_customer_id === 'string' && row.stripe_customer_id
    ? row.stripe_customer_id
    : undefined

  // The webhook reads metadata.tier to set user_tiers.tier; founding checkouts grant 'pro'.
  const metadata: Record<string, string> = isFounding
    ? { userId, tier: 'pro', founding: 'true' }
    : { userId, tier }
  const session = await stripe.checkout.sessions.create({
    mode: 'subscription',
    payment_method_types: ['card'],
    line_items: [{ price: priceId, quantity: 1 }],
    ...(existingCustomer ? { customer: existingCustomer } : {}),
    success_url: `${appUrl()}/dashboard?upgraded=true`,
    cancel_url: isFounding ? `${appUrl()}/dashboard/settings` : `${appUrl()}/dashboard/markets`,
    metadata,
    // Also stamp the Subscription itself so customer.subscription.* webhooks can resolve the user
    subscription_data: { metadata },
  })
  return NextResponse.json({ url: session.url })
}
