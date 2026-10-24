import { createClient as createSupabaseClient } from '@supabase/supabase-js'

function requireEnv(name: string): string {
  const value = process.env[name]
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`)
  }
  return value
}

// Fail at module load rather than silently falling back to a hardcoded project URL.
const SUPABASE_URL = requireEnv('NEXT_PUBLIC_SUPABASE_URL')
const SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || ''

export function createClient() {
  if (!SERVICE_ROLE_KEY) {
    throw new Error('SUPABASE_SERVICE_ROLE_KEY is not set')
  }
  return createSupabaseClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
    auth: { persistSession: false }
  })
}
