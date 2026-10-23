'use server'

import { auth } from '@clerk/nextjs/server'
import { createClient } from '@/lib/supabase/server'

export async function savePreferences(
  phone: string,
  smsEnabled: boolean,
  emailEnabled: boolean,
): Promise<{ ok: boolean; error?: string }> {
  const { userId } = await auth()
  if (!userId) return { ok: false, error: 'unauthenticated' }

  const supabase = createClient()

  const { error } = await supabase
    .from('user_preferences')
    .upsert(
      {
        user_id: userId,
        phone,
        sms_enabled: smsEnabled,
        email_enabled: emailEnabled,
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
