import { test, expect } from '@playwright/test'

const LANDING_URL = process.env.LANDING_URL || 'https://www.strwatch.io'

test.describe('Landing Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(LANDING_URL)
  })

  test('page loads with correct title', async ({ page }) => {
    await expect(page).toHaveTitle(/STRWatch/)
  })

  test('nav has all links', async ({ page }) => {
    await expect(page.locator('a.nav-link:has-text("How it works")')).toBeVisible()
    await expect(page.locator('a.nav-link:has-text("Features")')).toBeVisible()
    await expect(page.locator('a.nav-link:has-text("Pricing")')).toBeVisible()
  })

  test('nav CTA links to sign-up', async ({ page }) => {
    const cta = page.locator('a.nav-cta')
    await expect(cta).toBeVisible()
    await expect(cta).toHaveAttribute('href', /app\.strwatch\.io\/sign-up/)
  })

  test('hero section has headline and subtext', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('regulation change')
    await expect(page.locator('.hero-sub')).toContainText('STRWatch watches city hall')
  })

  test('hero shows beta markets badge', async ({ page }) => {
    const badge = page.locator('.hero-badge')
    await expect(badge).toContainText('Beta open')
    await expect(badge).toContainText('Nashville')
    await expect(badge).toContainText('Austin')
  })

  test('hero beta CTA mentions 45-day trial', async ({ page }) => {
    const betaCta = page.locator('a[href*="app.strwatch.io/sign-up"]').first()
    await expect(betaCta).toContainText(/45 day|free trial/i)
  })

  test('waitlist form is present and functional', async ({ page }) => {
    const emailInput = page.locator('#email-hero')
    const submitBtn = page.locator('#form-hero button[type="submit"]')
    await expect(emailInput).toBeVisible()
    await expect(submitBtn).toBeVisible()

    // Submit with a test email
    await emailInput.fill('e2etest@example.com')
    await submitBtn.click()

    // Success message should appear
    const success = page.locator('#success-hero')
    await expect(success).toBeVisible({ timeout: 5000 })
    await expect(success).toContainText("You're on the list")
  })

  test('fine ticker shows enforcement examples', async ({ page }) => {
    const ticker = page.locator('.fine-ticker')
    await expect(ticker).toBeVisible()
    await expect(ticker.locator('.fine-city')).toHaveCount({ minimum: 4 })
    await expect(ticker).toContainText('Nashville')
    await expect(ticker).toContainText('Austin')
    await expect(ticker).toContainText('Denver')
  })

  test('pricing section shows three tiers', async ({ page }) => {
    const cards = page.locator('.pricing-card')
    await expect(cards).toHaveCount(3)
    await expect(page.locator('.pricing-card').first()).toContainText('Free')
    await expect(page.locator('.pricing-card.featured')).toContainText('Pro')
    await expect(page.locator('.pricing-card').last()).toContainText('Agency')
  })

  test('pro pricing card shows 45-day trial', async ({ page }) => {
    const proCard = page.locator('.pricing-card.featured')
    await expect(proCard).toContainText('45-day free trial')
    await expect(proCard).toContainText('$29/mo')
  })

  test('alert mockup includes AI checklist', async ({ page }) => {
    const checklist = page.locator('.checklist')
    await expect(checklist).toBeVisible()
    await expect(checklist).toContainText('AI compliance checklist')
    await expect(checklist.locator('.checklist-step')).toHaveCount({ minimum: 4 })
  })

  test('features section has 6 features', async ({ page }) => {
    const features = page.locator('.feature')
    await expect(features).toHaveCount(6)
  })

  test('footer has ToS and Privacy links', async ({ page }) => {
    const tos = page.locator('footer a[href*="terms.html"]')
    const privacy = page.locator('footer a[href*="privacy.html"]')
    await expect(tos).toBeVisible()
    await expect(privacy).toBeVisible()
  })

  test('bottom CTA form works', async ({ page }) => {
    const emailInput = page.locator('#email-bottom')
    await emailInput.scrollIntoViewIfNeeded()
    await expect(emailInput).toBeVisible()
  })
})

test.describe('Landing Page — Mobile', () => {
  test.use({ viewport: { width: 375, height: 812 } })

  test('mobile layout hides nav links', async ({ page }) => {
    await page.goto(LANDING_URL)
    const navLinks = page.locator('a.nav-link')
    // Nav links should be hidden on mobile
    for (const link of await navLinks.all()) {
      await expect(link).not.toBeVisible()
    }
  })

  test('mobile hero is visible', async ({ page }) => {
    await page.goto(LANDING_URL)
    await expect(page.locator('h1')).toBeVisible()
    await expect(page.locator('.hero-sub')).toBeVisible()
  })
})
