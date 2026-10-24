import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import Stripe from 'stripe'

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
  const required = ['STRIPE_SECRET_KEY', 'STRIPE_PRICE_PRO', 'STRIPE_PRICE_AGENCY'] as const
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
      pro:    values.STRIPE_PRICE_PRO!,
      agency: values.STRIPE_PRICE_AGENCY!,
    },
  }
}

export async function POST(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  const { secretKey, priceIds } = getStripeEnv()
  const stripe = new Stripe(secretKey, { apiVersion: '2026-02-25.clover' })
  const { tier } = await req.json()
  const priceId = priceIds[tier]
  if (!priceId) return NextResponse.json({ error: 'Invalid tier' }, { status: 400 })
  const session = await stripe.checkout.sessions.create({
    mode: 'subscription',
    payment_method_types: ['card'],
    line_items: [{ price: priceId, quantity: 1 }],
    success_url: `${process.env.NEXT_PUBLIC_APP_URL}/dashboard?upgraded=true`,
    cancel_url: `${process.env.NEXT_PUBLIC_APP_URL}/dashboard/markets`,
    metadata: { userId, tier },
    // Also stamp the Subscription itself so customer.subscription.* webhooks can resolve the user
    subscription_data: { metadata: { userId, tier } },
  })
  return NextResponse.json({ url: session.url })
}
