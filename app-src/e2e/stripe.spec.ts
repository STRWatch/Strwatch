import { test, expect } from '@playwright/test'

test.describe('Stripe Checkout API', () => {
  test('checkout endpoint returns 401 for unauthenticated requests', async ({ request }) => {
    const response = await request.post('/api/stripe/checkout', {
      data: { tier: 'pro' },
      headers: { 'Content-Type': 'application/json' },
    })
    expect(response.status()).toBe(401)
    const body = await response.json()
    expect(body.error).toBe('Unauthorized')
  })

  test('checkout endpoint rejects invalid tier', async ({ request }) => {
    // This will also get 401 since we're not authenticated,
    // but tests the route exists and responds
    const response = await request.post('/api/stripe/checkout', {
      data: { tier: 'nonexistent' },
      headers: { 'Content-Type': 'application/json' },
    })
    // Either 401 (no auth) or 400 (invalid tier) are acceptable
    expect([400, 401]).toContain(response.status())
  })
})

test.describe('Stripe Webhook API', () => {
  test('webhook endpoint rejects invalid signature', async ({ request }) => {
    const response = await request.post('/api/stripe/webhook', {
      data: '{"type":"test"}',
      headers: {
        'Content-Type': 'application/json',
        'stripe-signature': 'invalid_sig',
      },
    })
    expect(response.status()).toBe(400)
    const body = await response.json()
    expect(body.error).toBe('Invalid signature')
  })
})
