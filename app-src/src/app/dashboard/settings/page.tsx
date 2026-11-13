import { auth } from '@clerk/nextjs/server'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import SettingsClient from './SettingsClient'
import { getEffectiveTier } from '@/lib/tier'

export default async function SettingsPage({
  searchParams,
}: {
  searchParams: Promise<{ upgrade?: string }>
}) {
  const { userId } = await auth()
  if (!userId) redirect('/sign-in')
  const supabase = createClient()

  const { data: prefs } = await supabase
    .from('user_preferences')
    .select('*')
    .eq('user_id', userId)
    .single()

  const { data: tierRow } = await supabase
    .from('user_tiers')
    .select('stripe_customer_id, founding_member')
    .eq('user_id', userId)
    .maybeSingle()
  const hasBilling = !!tierRow?.stripe_customer_id
  const { upgrade } = await searchParams
  // Founding offer: only for flagged users who arrive via the day-35 email link, and only if not already paying.
  const showFoundingOffer = upgrade === 'founding' && !!tierRow?.founding_member && !hasBilling

  const { tier, isPaid, isAgency, isTrialActive } = await getEffectiveTier(userId)
  // Must match the server gate in savePreferences: paid, agency, or active Pro trial.
  const isPro = isPaid || isAgency || isTrialActive

  return <SettingsClient
    phone={prefs?.phone || ''}
    smsEnabled={prefs?.sms_enabled ?? true}
    emailEnabled={prefs?.email_enabled ?? true}
    isPro={isPro}
    tier={tier}
    hasBilling={hasBilling}
    showFoundingOffer={showFoundingOffer}
  />
}
