import Stripe from 'stripe'

export const STRIPE_API_VERSION = '2026-02-25.clover' as const

/**
 * Stripe client, constructed per call so STRIPE_SECRET_KEY is read at request
 * time. `new Stripe(undefined)` throws, and `next build` evaluates route
 * modules without runtime env, so nothing here may run at module load.
 */
export function getStripe(): Stripe {
  const secretKey = process.env.STRIPE_SECRET_KEY
  if (!secretKey) {
    throw new Error('Missing required environment variable: STRIPE_SECRET_KEY')
  }
  return new Stripe(secretKey, { apiVersion: STRIPE_API_VERSION })
}
