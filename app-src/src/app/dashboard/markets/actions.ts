'use server'

import { createClient } from '@/lib/supabase/server'

export async function addMarket(userId: string, city: string): Promise<{ ok: boolean }> {
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

export async function removeMarket(userId: string, city: string): Promise<{ ok: boolean }> {
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
