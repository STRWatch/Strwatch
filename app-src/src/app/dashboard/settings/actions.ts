'use server'

import { auth } from '@clerk/nextjs/server'
import { createClient } from '@/lib/supabase/server'
import { getEffectiveTier } from '@/lib/tier'

// E.164, US only: +1 followed by exactly 10 digits. Empty string clears the number.
const PHONE_E164_US = /^\+1\d{10}$/

export async function savePreferences(
  phone: string,
  smsEnabled: boolean,
  emailEnabled: boolean,
): Promise<{ ok: boolean; error?: string }> {
  const { userId } = await auth()
  if (!userId) return { ok: false, error: 'unauthenticated' }

  if (typeof phone !== 'string' || (phone !== '' && !PHONE_E164_US.test(phone))) {
    return { ok: false, error: 'invalid_phone' }
  }

  if (smsEnabled === true) {
    const { isPaid, isAgency, isTrialActive } = await getEffectiveTier(userId)
    if (!(isPaid || isAgency || isTrialActive)) return { ok: false, error: 'sms_requires_pro' }
  }

  const supabase = createClient()

  const { error } = await supabase
    .from('user_preferences')
    .upsert(
      {
        user_id: userId,
        phone,
        sms_enabled: smsEnabled === true,
        email_enabled: emailEnabled === true,
        updated_at: new Date().toISOString(),
      },
      { onConflict: 'user_id' }
    )

  if (error) {
    console.error('savePreferences error:', error)
    return { ok: false }
  }
  return { ok: true }
}
