import { createClient as createSupabaseClient } from '@supabase/supabase-js'

function requireEnv(name: string): string {
  const value = process.env[name]
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`)
  }
  return value
}

/**
 * Service-role Supabase client for server code.
 *
 * Env is read on each call, not at module load. `next build` evaluates every
 * route module while collecting page data, before runtime env exists, so a
 * module-level check would fail the build. Reading lazily keeps the loud
 * error but moves it to the first request that actually needs the client.
 */
export function createClient() {
  const supabaseUrl = requireEnv('NEXT_PUBLIC_SUPABASE_URL')
  const serviceRoleKey = requireEnv('SUPABASE_SERVICE_ROLE_KEY')
  return createSupabaseClient(supabaseUrl, serviceRoleKey, {
    auth: { persistSession: false }
  })
}
