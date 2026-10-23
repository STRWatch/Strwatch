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

  const { tier, isPaid, isAgency } = await getEffectiveTier(userId)
  // SMS is paid-only server-side (savePreferences), so the UI gate must match.
  const isPro = isPaid || isAgency

  return <SettingsClient
    phone={prefs?.phone || ''}
    smsEnabled={prefs?.sms_enabled ?? true}
    emailEnabled={prefs?.email_enabled ?? true}
    isPro={isPro}
    tier={tier}
  />
}
