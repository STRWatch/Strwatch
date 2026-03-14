import { auth } from '@clerk/nextjs/server'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import ScansClient from './ScansClient'

export default async function ScansPage() {
  const { userId } = await auth()
  if (!userId) redirect('/sign-in')
  const supabase = createClient()

  const { data: tierData } = await supabase
    .from('user_tiers')
    .select('tier, trial_ends_at')
    .eq('user_id', userId)
    .single()

  const now = new Date()
  const tier = tierData?.tier || 'free'
  const trialEndsAt = tierData?.trial_ends_at ? new Date(tierData.trial_ends_at) : null
  const isTrialActive = trialEndsAt && trialEndsAt > now && tier === 'pro'
  const canScan = tier === 'pro' || tier === 'agency' || isTrialActive

  const { data: scans } = await supabase
    .from('scans')
    .select('id, city, is_enriched, created_at, report')
    .eq('user_id', userId)
    .order('created_at', { ascending: false })
    .limit(20)

  return <ScansClient
    userId={userId}
    scans={scans || []}
    canScan={canScan || false}
    tier={tier}
  />
}
