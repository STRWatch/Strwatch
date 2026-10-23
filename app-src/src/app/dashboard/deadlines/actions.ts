'use server'

import { auth } from '@clerk/nextjs/server'
import { createClient } from '@/lib/supabase/server'

export async function addDeadline(
  city: string,
  title: string,
  deadlineDate: string,
  description: string,
): Promise<{ ok: boolean; error?: string }> {
  const { userId } = await auth()
  if (!userId) return { ok: false, error: 'unauthenticated' }

  const supabase = createClient()
  const { error } = await supabase.from('deadlines').insert({
    user_id: userId,
    city,
    title,
    deadline_date: deadlineDate,
    description: description || null,
    category: 'custom',
  })
  if (error) {
    console.error('addDeadline error:', error)
    return { ok: false }
  }
  return { ok: true }
}

export async function removeDeadline(
  deadlineId: string,
): Promise<{ ok: boolean; error?: string }> {
  const { userId } = await auth()
  if (!userId) return { ok: false, error: 'unauthenticated' }

  const supabase = createClient()
  // Only allow deleting user's own custom deadlines
  const { error } = await supabase
    .from('deadlines')
    .delete()
    .eq('id', deadlineId)
    .eq('user_id', userId)
  if (error) {
    console.error('removeDeadline error:', error)
    return { ok: false }
  }
  return { ok: true }
}
