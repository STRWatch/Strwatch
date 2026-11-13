import { auth } from '@clerk/nextjs/server'
import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { getStripe } from '@/lib/stripe'

export async function POST() {
  const { userId } = await auth()
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const supabase = createClient()
  const { data, error } = await supabase
    .from('user_tiers')
    .select('stripe_customer_id')
    .eq('user_id', userId)
    .maybeSingle()
  if (error) {
    console.error('stripe/portal user_tiers lookup error:', error)
    return NextResponse.json({ error: 'db' }, { status: 500 })
  }
  const customer = data?.stripe_customer_id
  if (!customer) {
    return NextResponse.json({ error: 'No billing account on file' }, { status: 403 })
  }

  const stripe = getStripe()
  const session = await stripe.billingPortal.sessions.create({
    customer,
    return_url: `${process.env.NEXT_PUBLIC_APP_URL}/dashboard/settings`,
  })
  return NextResponse.json({ url: session.url })
}
