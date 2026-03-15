import { auth } from '@clerk/nextjs/server'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import SettingsClient from './SettingsClient'

export default async function SettingsPage() {
  const { userId } = await auth()
  if (!userId) redirect('/sign-in')
  const supabase = createClient()

  const { data: prefs } = await supabase
    .from('user_preferences')
    .select('*')
    .eq('user_id', userId)
    .single()

  const { data: tierData } = await supabase
    .from('user_tiers')
    .select('tier, trial_ends_at')
    .eq('user_id', userId)
    .single()

  const now = new Date()
  const tier = tierData?.tier || 'free'
  const trialEndsAt = tierData?.trial_ends_at ? new Date(tierData.trial_ends_at) : null
  const isTrialActive = trialEndsAt && trialEndsAt > now && tier === 'pro'
  const isPro = tier === 'pro' || tier === 'agency' || isTrialActive

  return <SettingsClient
    userId={userId}
    phone={prefs?.phone || ''}
    smsEnabled={prefs?.sms_enabled ?? true}
    emailEnabled={prefs?.email_enabled ?? true}
    isPro={isPro || false}
    tier={tier}
  />
}
