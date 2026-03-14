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
    .select('city')
    .eq('user_id', userId)

  const savedCities = (userMarkets || []).map((m: { city: string }) => m.city)

  return <MarketsClient userId={userId} savedCities={savedCities} />
}
