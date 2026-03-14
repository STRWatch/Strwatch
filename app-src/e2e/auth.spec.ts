import { test, expect } from '@playwright/test'

test.describe('Authentication', () => {
  test('redirects unauthenticated users from dashboard to sign-in', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/sign-in/)
  })

  test('redirects unauthenticated users from markets to sign-in', async ({ page }) => {
    await page.goto('/dashboard/markets')
    await expect(page).toHaveURL(/sign-in/)
  })

  test('redirects unauthenticated users from deadlines to sign-in', async ({ page }) => {
    await page.goto('/dashboard/deadlines')
    await expect(page).toHaveURL(/sign-in/)
  })

  test('redirects unauthenticated users from alerts to sign-in', async ({ page }) => {
    await page.goto('/dashboard/alerts')
    await expect(page).toHaveURL(/sign-in/)
  })

  test('sign-in page loads', async ({ page }) => {
    await page.goto('/sign-in')
    await expect(page).toHaveURL(/sign-in/)
    // Clerk widget should be present
    await expect(page.locator('.cl-rootBox, .cl-signIn-root, [data-clerk]')).toBeVisible({ timeout: 10000 })
  })

  test('sign-up page loads', async ({ page }) => {
    await page.goto('/sign-up')
    await expect(page).toHaveURL(/sign-up/)
    await expect(page.locator('.cl-rootBox, .cl-signUp-root, [data-clerk]')).toBeVisible({ timeout: 10000 })
  })

  test('sign-up page shows ToS and Privacy links', async ({ page }) => {
    await page.goto('/sign-up')
    const tosLink = page.locator('a[href*="terms.html"]')
    const privacyLink = page.locator('a[href*="privacy.html"]')
    await expect(tosLink).toBeVisible({ timeout: 10000 })
    await expect(privacyLink).toBeVisible({ timeout: 10000 })
  })

  test('root page redirects to sign-in when unauthenticated', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveURL(/sign-in/)
  })
})
