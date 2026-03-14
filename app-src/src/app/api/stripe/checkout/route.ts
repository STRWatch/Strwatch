import { auth } from '@clerk/nextjs/server'
import { NextRequest, NextResponse } from 'next/server'
import Stripe from 'stripe'

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, { apiVersion: '2024-12-18.acacia' })

const PRICE_IDS: Record<string, string> = {
  pro:    process.env.STRIPE_PRICE_PRO!,
  agency: process.env.STRIPE_PRICE_AGENCY!,
}

export async function POST(req: NextRequest) {
  const { userId } = await auth()
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  const { tier } = await req.json()
  const priceId = PRICE_IDS[tier]
  if (!priceId) return NextResponse.json({ error: 'Invalid tier' }, { status: 400 })
  const session = await stripe.checkout.sessions.create({
    mode: 'subscription',
    payment_method_types: ['card'],
    line_items: [{ price: priceId, quantity: 1 }],
    success_url: `${process.env.NEXT_PUBLIC_APP_URL}/dashboard?upgraded=true`,
    cancel_url: `${process.env.NEXT_PUBLIC_APP_URL}/dashboard/markets`,
    metadata: { userId, tier },
  })
  return NextResponse.json({ url: session.url })
}
