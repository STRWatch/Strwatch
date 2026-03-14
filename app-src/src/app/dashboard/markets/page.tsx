import { auth } from '@clerk/nextjs/server'
import { redirect } from 'next/navigation'
import MarketsClient from './MarketsClient'
import { createClient } from '@/lib/supabase/server'

export default async function MarketsPage() {
  const { userId } = await auth()
  if (!userId) redirect('/sign-in')

  const supabase = createClient()

  const { data: userMarkets } = await supabase
    .from('user_markets')
    .select('city, added_at')
    .eq('user_id', userId)
    .order('added_at', { ascending: true })

  const { data: tierData } = await supabase
    .from('user_tiers')
    .select('tier')
    .eq('user_id', userId)
    .single()

  const tier = tierData?.tier || 'free'
  const savedCities = (userMarkets || []).map((m: { city: string }) => m.city)
  const maxMarkets = tier === 'free' ? 1 : 999

  return <MarketsClient userId={userId} savedCities={savedCities} tier={tier} maxMarkets={maxMarkets} />
}
