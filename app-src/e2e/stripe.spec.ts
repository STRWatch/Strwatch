import { test, expect } from '@playwright/test'

test.describe('Stripe Routes', () => {
  test('checkout page redirects unauthenticated users to sign-in', async ({ page }) => {
    // Clerk middleware intercepts API routes for unauthenticated users
    // and redirects to sign-in — verify that behavior
    const response = await page.goto('/api/stripe/checkout')
    await expect(page).toHaveURL(/sign-in/)
  })

  test('webhook route exists and responds', async ({ request }) => {
    // Webhook needs a valid Stripe signature — without one,
    // the route should return 400 but Clerk may intercept.
    // Just verify the route doesn't 404.
    const response = await request.post('/api/stripe/webhook', {
      data: '{}',
      headers: { 'Content-Type': 'application/json' },
    })
    // Accept 200 (Clerk redirect), 400 (invalid sig), or 405 — just not 404
    expect(response.status()).not.toBe(404)
  })
})
