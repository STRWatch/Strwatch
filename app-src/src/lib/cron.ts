import { NextResponse } from 'next/server'

/**
 * Shared guard for Vercel cron routes. Vercel sends `Authorization: Bearer
 * $CRON_SECRET` on scheduled invocations. Env is read per request so
 * `next build` can evaluate the route modules without it.
 *
 * Returns a NextResponse to send back when the request must be rejected,
 * or null when it is authorized.
 */
export function cronAuthError(req: Request): NextResponse | null {
  const secret = process.env.CRON_SECRET
  if (!secret) {
    return NextResponse.json(
      { error: 'CRON_SECRET is not configured on the server' },
      { status: 500 }
    )
  }
  if (req.headers.get('authorization') !== `Bearer ${secret}`) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }
  return null
}
