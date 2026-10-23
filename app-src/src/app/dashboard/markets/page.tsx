import { auth } from '@clerk/nextjs/server'
import { redirect } from 'next/navigation'
import MarketsClient from './MarketsClient'
import { createClient } from '@/lib/supabase/server'
import { getEffectiveTier } from '@/lib/tier'

export default async function MarketsPage() {
  const { userId } = await auth()
  if (!userId) redirect('/sign-in')

  const supabase = createClient()

  const { tier: effectiveTier, isTrialActive, isPaid, trialEndsAt } = await getEffectiveTier(userId)
  const now = new Date()
  const trialDaysLeft = isTrialActive && trialEndsAt
    ? Math.ceil((trialEndsAt.getTime() - now.getTime()) / 86400000)
    : 0

  const { data: userMarkets } = await supabase
    .from('user_markets')
    .select('city, added_at')
    .eq('user_id', userId)
    .order('added_at', { ascending: true })

  const savedCities = (userMarkets || []).map((m: { city: string }) => m.city)
  const maxMarkets = effectiveTier === 'free' ? 1 : 999

  return <MarketsClient
    savedCities={savedCities}
    tier={effectiveTier}
    maxMarkets={maxMarkets}
    trialDaysLeft={trialDaysLeft}
    isTrialActive={isTrialActive}
    isPaid={isPaid}
  />
}
