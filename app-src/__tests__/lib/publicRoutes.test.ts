import { describe, it, expect } from 'vitest'
import { createRouteMatcher } from '@clerk/nextjs/server'
import { NextRequest } from 'next/server'
import { PUBLIC_ROUTES } from '@/lib/publicRoutes'

const isPublic = createRouteMatcher(PUBLIC_ROUTES)
const req = (path: string) => new NextRequest(`https://app.strwatch.io${path}`)

describe('PUBLIC_ROUTES', () => {
  it('leaves the Vercel cron routes to CRON_SECRET, not Clerk', () => {
    expect(isPublic(req('/api/cron/tiers'))).toBe(true)
    expect(isPublic(req('/api/cron/emails?dry_run=1'))).toBe(true)
  })
  it('keeps the Stripe webhook and auth pages public', () => {
    expect(isPublic(req('/api/stripe/webhook'))).toBe(true)
    expect(isPublic(req('/sign-in'))).toBe(true)
  })
  it('protects everything else', () => {
    expect(isPublic(req('/dashboard'))).toBe(false)
    expect(isPublic(req('/api/stripe/checkout'))).toBe(false)
    expect(isPublic(req('/admin'))).toBe(false)
  })
})
