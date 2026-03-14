import { describe, it, expect, vi } from 'vitest'

// Mock supabase client
vi.mock('@supabase/supabase-js', () => ({
  createClient: vi.fn(() => ({
    from: vi.fn(() => ({
      select: vi.fn(() => Promise.resolve({ data: [], error: null })),
      insert: vi.fn(() => Promise.resolve({ data: null, error: null })),
    })),
  })),
}))

describe('supabase client', () => {
  it('should export a supabase client', async () => {
    const { supabase } = await import('@/lib/supabase')
    expect(supabase).toBeDefined()
  })
})
