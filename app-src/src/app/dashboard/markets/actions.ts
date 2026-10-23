'use server'

import { auth } from '@clerk/nextjs/server'
import { createClient } from '@/lib/supabase/server'
import { getEffectiveTier } from '@/lib/tier'
import { isKnownMarket } from '@/lib/markets'

const FREE_TIER_MARKET_LIMIT = 1

export async function addMarket(city: string): Promise<{ ok: boolean; error?: string }> {
  const { userId } = await auth()
  if (!userId) return { ok: false, error: 'unauthenticated' }

  if (typeof city !== 'string' || !isKnownMarket(city)) {
    return { ok: false, error: 'invalid_city' }
  }

  const supabase = createClient()
  const { tier } = await getEffectiveTier(userId)

  if (tier === 'free') {
    const { count, error: countError } = await supabase
      .from('user_markets')
      .select('city', { count: 'exact', head: true })
      .eq('user_id', userId)
    if (countError) {
      console.error('addMarket count error:', countError)
      return { ok: false }
    }
    if ((count ?? 0) >= FREE_TIER_MARKET_LIMIT) {
      return { ok: false, error: 'market_limit' }
    }
  }

  const { error } = await supabase
    .from('user_markets')
    .insert({ user_id: userId, city })
  if (error) {
    console.error('addMarket error:', error)
    return { ok: false }
  }
  return { ok: true }
}

export async function removeMarket(city: string): Promise<{ ok: boolean; error?: string }> {
  const { userId } = await auth()
  if (!userId) return { ok: false, error: 'unauthenticated' }

  // Free plan: markets are locked (mirrors the UI rule, now enforced server-side)
  const { tier } = await getEffectiveTier(userId)
  if (tier === 'free') return { ok: false, error: 'free_tier_locked' }

  const supabase = createClient()
  const { error } = await supabase
    .from('user_markets')
    .delete()
    .eq('user_id', userId)
    .eq('city', city)
  if (error) {
    console.error('removeMarket error:', error)
    return { ok: false }
  }
  return { ok: true }
}
