import { auth } from '@clerk/nextjs/server'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import SettingsClient from './SettingsClient'
import { getEffectiveTier } from '@/lib/tier'

export default async function SettingsPage() {
  const { userId } = await auth()
  if (!userId) redirect('/sign-in')
  const supabase = createClient()

  const { data: prefs } = await supabase
    .from('user_preferences')
    .select('*')
    .eq('user_id', userId)
    .single()

  const { tier, isPaid, isAgency, isTrialActive } = await getEffectiveTier(userId)
  // Must match the server gate in savePreferences: paid, agency, or active Pro trial.
  const isPro = isPaid || isAgency || isTrialActive

  return <SettingsClient
    phone={prefs?.phone || ''}
    smsEnabled={prefs?.sms_enabled ?? true}
    emailEnabled={prefs?.email_enabled ?? true}
    isPro={isPro}
    tier={tier}
  />
}
