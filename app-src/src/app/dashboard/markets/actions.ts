'use server'

import { auth } from '@clerk/nextjs/server'
import { createClient } from '@/lib/supabase/server'

export async function addMarket(city: string): Promise<{ ok: boolean; error?: string }> {
  const { userId } = await auth()
  if (!userId) return { ok: false, error: 'unauthenticated' }

  const supabase = createClient()
  const { error } = await supabase
    .from('user_markets')
    .insert({ user_id: userId, city })
  if (error) {
    console.error('addMarket error:', error)
    return { ok: false }
  }
  return { ok: true }
}

export async function removeMarket(city: string): Promise<{ ok: boolean; error?: string }> {
  const { userId } = await auth()
  if (!userId) return { ok: false, error: 'unauthenticated' }

  const supabase = createClient()
  const { error } = await supabase
    .from('user_markets')
    .delete()
    .eq('user_id', userId)
    .eq('city', city)
  if (error) {
    console.error('removeMarket error:', error)
    return { ok: false }
  }
  return { ok: true }
}
