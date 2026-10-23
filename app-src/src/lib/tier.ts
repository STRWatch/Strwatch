import { createClient } from '@/lib/supabase/server'

export const TRIAL_DAYS = 45

export type Tier = 'free' | 'pro' | 'agency'

export type EffectiveTier = {
  /** Tier after applying trial expiry (an expired 'pro' trial reads as 'free'). */
  tier: Tier
  isTrialActive: boolean
  /** Paying subscriber: 'pro' with no trial in flight, or 'agency'. */
  isPaid: boolean
  isAgency: boolean
  trialEndsAt: Date | null
}

/**
 * Bootstraps a 45-day Pro trial row for first-time users (atomic: upsert with
 * ignoreDuplicates so concurrent first loads cannot double-insert), lazily
 * downgrades an expired trial to 'free', and returns the effective tier.
 *
 * Single source of truth for tier decisions on the server — pages, server
 * actions and API routes must all go through this.
 */
export async function getEffectiveTier(userId: string): Promise<EffectiveTier> {
  const supabase = createClient()
  const now = new Date()

  const trialEnd = new Date(now)
  trialEnd.setDate(trialEnd.getDate() + TRIAL_DAYS)
  const { error: bootstrapError } = await supabase
    .from('user_tiers')
    .upsert(
      {
        user_id: userId,
        tier: 'pro',
        trial_ends_at: trialEnd.toISOString(),
        updated_at: now.toISOString(),
      },
      { onConflict: 'user_id', ignoreDuplicates: true }
    )
  if (bootstrapError) console.error('getEffectiveTier bootstrap error:', bootstrapError)

  const { data } = await supabase
    .from('user_tiers')
    .select('tier, trial_ends_at')
    .eq('user_id', userId)
    .single()

  const rawTier: Tier = data?.tier === 'pro' || data?.tier === 'agency' ? data.tier : 'free'
  const trialEndsAt = data?.trial_ends_at ? new Date(data.trial_ends_at) : null
  const isTrialActive = rawTier === 'pro' && trialEndsAt !== null && trialEndsAt > now
  const isTrialExpired = rawTier === 'pro' && trialEndsAt !== null && trialEndsAt <= now

  if (isTrialExpired) {
    const { error } = await supabase
      .from('user_tiers')
      .update({ tier: 'free', updated_at: now.toISOString() })
      .eq('user_id', userId)
    if (error) console.error('getEffectiveTier downgrade error:', error)
  }

  const tier: Tier = isTrialExpired ? 'free' : rawTier
  const isAgency = tier === 'agency'
  const isPaid = (tier === 'pro' && !isTrialActive) || isAgency

  return { tier, isTrialActive, isPaid, isAgency, trialEndsAt }
}
