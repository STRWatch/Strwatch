import { test, expect } from '@playwright/test'

const LANDING_URL = process.env.LANDING_URL || 'https://www.strwatch.io'

test.describe('Terms of Service', () => {
  test('page loads', async ({ page }) => {
    await page.goto(`${LANDING_URL}/terms.html`)
    await expect(page).toHaveTitle(/Terms of Service/)
  })

  test('has all required sections', async ({ page }) => {
    await page.goto(`${LANDING_URL}/terms.html`)
    const content = page.locator('.content')
    await expect(content).toContainText('Agreement to Terms')
    await expect(content).toContainText('Description of Service')
    await expect(content).toContainText('Subscription Plans')
    await expect(content).toContainText('Cancellation')
    await expect(content).toContainText('Limitation of Liability')
    await expect(content).toContainText('Governing Law')
  })

  test('mentions 45-day trial and $29/mo pricing', async ({ page }) => {
    await page.goto(`${LANDING_URL}/terms.html`)
    await expect(page.locator('.content')).toContainText('$29')
  })

  test('has back-to-home link', async ({ page }) => {
    await page.goto(`${LANDING_URL}/terms.html`)
    const backLink = page.locator('a:has-text("Back to home")')
    await expect(backLink).toBeVisible()
  })

  test('footer links to privacy policy', async ({ page }) => {
    await page.goto(`${LANDING_URL}/terms.html`)
    const privacyLink = page.locator('footer a[href*="privacy.html"]')
    await expect(privacyLink).toBeVisible()
  })
})

test.describe('Privacy Policy', () => {
  test('page loads', async ({ page }) => {
    await page.goto(`${LANDING_URL}/privacy.html`)
    await expect(page).toHaveTitle(/Privacy Policy/)
  })

  test('has all required sections', async ({ page }) => {
    await page.goto(`${LANDING_URL}/privacy.html`)
    const content = page.locator('.content')
    await expect(content).toContainText('Who We Are')
    await expect(content).toContainText('Information We Collect')
    await expect(content).toContainText('Third-Party Services')
    await expect(content).toContainText('Cookies')
    await expect(content).toContainText('Data Retention')
    await expect(content).toContainText('Your Rights')
    await expect(content).toContainText('California Residents')
  })

  test('lists all third-party services', async ({ page }) => {
    await page.goto(`${LANDING_URL}/privacy.html`)
    const content = page.locator('.content')
    await expect(content).toContainText('Clerk')
    await expect(content).toContainText('Supabase')
    await expect(content).toContainText('Stripe')
    await expect(content).toContainText('Resend')
    await expect(content).toContainText('Twilio')
    await expect(content).toContainText('Vercel')
  })

  test('has contact email', async ({ page }) => {
    await page.goto(`${LANDING_URL}/privacy.html`)
    await expect(page.locator('.content')).toContainText('privacy@strwatch.io')
  })

  test('footer links to terms of service', async ({ page }) => {
    await page.goto(`${LANDING_URL}/privacy.html`)
    const tosLink = page.locator('footer a[href*="terms.html"]')
    await expect(tosLink).toBeVisible()
  })
})
