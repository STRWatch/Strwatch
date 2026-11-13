/**
 * Routes Clerk middleware must not protect. Everything else requires a session.
 * Kept out of middleware.ts so it can be unit-tested without the edge runtime.
 */
export const PUBLIC_ROUTES = [
  '/sign-in(.*)',
  '/sign-up(.*)',
  '/api/stripe/webhook',
  // Vercel cron invocations carry only `Authorization: Bearer $CRON_SECRET`;
  // lib/cron.ts verifies that header. Without this entry Clerk's protect()
  // returns 404 before the handler runs.
  '/api/cron(.*)',
]
