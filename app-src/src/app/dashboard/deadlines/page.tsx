import { auth } from '@clerk/nextjs/server'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import DeadlinesClient from './DeadlinesClient'

export default async function DeadlinesPage() {
  const { userId } = await auth()
  if (!userId) redirect('/sign-in')
  const supabase = createClient()

  const { data: markets } = await supabase
    .from('user_markets')
    .select('city')
    .eq('user_id', userId)

  const userCities = (markets || []).map((m: {city:string}) => m.city)

  let deadlines: any[] = []
  if (userCities.length > 0) {
    // Fetch both city-level deadlines (user_id IS NULL) and user's custom deadlines
    const { data } = await supabase
      .from('deadlines')
      .select('*')
      .or(`user_id.is.null,user_id.eq.${userId}`)
      .in('city', userCities)
      .order('deadline_date', { ascending: true })
    deadlines = data || []
  }

  return <DeadlinesClient userId={userId} deadlines={deadlines} userCities={userCities} />
}
