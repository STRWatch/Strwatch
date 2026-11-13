import { auth } from '@clerk/nextjs/server'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { getEffectiveTier } from '@/lib/tier'
import ScansClient from './ScansClient'

export default async function ScansPage() {
  const { userId } = await auth()
  if (!userId) redirect('/sign-in')
  const supabase = createClient()

  // Same decision /api/scans/generate makes: an expired trial reads as free.
  const { tier, isPaid, isTrialActive } = await getEffectiveTier(userId)
  const canScan = isPaid || isTrialActive

  const { data: scans } = await supabase
    .from('scans')
    .select('id, city, is_enriched, created_at, report')
    .eq('user_id', userId)
    .order('created_at', { ascending: false })
    .limit(20)

  return <ScansClient
    userId={userId}
    scans={scans || []}
    canScan={canScan}
    tier={tier}
  />
}
