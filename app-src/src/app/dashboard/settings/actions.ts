'use server'

import { createClient } from '@/lib/supabase/server'

export async function savePreferences(
  userId: string,
  phone: string,
  smsEnabled: boolean,
  emailEnabled: boolean,
): Promise<{ ok: boolean }> {
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
