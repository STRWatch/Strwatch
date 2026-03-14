import { auth } from '@clerk/nextjs/server'
import { redirect } from 'next/navigation'
import MarketsClient from './MarketsClient'
import { createClient } from '@/lib/supabase/server'

const TRIAL_DAYS = 45

export default async function MarketsPage() {
  const { userId } = await auth()
  if (!userId) redirect('/sign-in')

  const supabase = createClient()

  const { data: tierData } = await supabase
    .from('user_tiers')
    .select('tier, trial_ends_at, updated_at')
    .eq('user_id', userId)
    .single()

  if (!tierData) {
    const trialEnd = new Date()
    trialEnd.setDate(trialEnd.getDate() + TRIAL_DAYS)
    await supabase.from('user_tiers').insert({
      user_id: userId,
      tier: 'pro',
      trial_ends_at: trialEnd.toISOString(),
      updated_at: new Date().toISOString(),
    })
  }

  const { data: currentTier } = await supabase
    .from('user_tiers')
    .select('tier, trial_ends_at, updated_at')
    .eq('user_id', userId)
    .single()

  const now = new Date()
  const trialEndsAt = currentTier?.trial_ends_at ? new Date(currentTier.trial_ends_at) : null
  const isTrialActive = trialEndsAt && trialEndsAt > now && currentTier?.tier === 'pro'
  const isTrialExpired = trialEndsAt && trialEndsAt <= now && currentTier?.tier === 'pro'

  if (isTrialExpired) {
    await supabase.from('user_tiers').update({
      tier: 'free',
      updated_at: new Date().toISOString(),
    }).eq('user_id', userId)
  }

  const effectiveTier = isTrialExpired ? 'free' : (currentTier?.tier || 'free')
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
  const isPaid = effectiveTier === 'pro' && !isTrialActive && !isTrialExpired
    || effectiveTier === 'agency'

  return <MarketsClient
    userId={userId}
    savedCities={savedCities}
    tier={effectiveTier}
    maxMarkets={maxMarkets}
    trialDaysLeft={trialDaysLeft}
    isTrialActive={isTrialActive || false}
    isPaid={isPaid}
  />
}
