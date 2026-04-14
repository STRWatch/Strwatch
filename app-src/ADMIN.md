# Admin Dashboard

The `/admin` route shows account and usage metrics for STRWatch. Access is restricted to Clerk user IDs listed in the `ADMIN_USER_IDS` environment variable.

## Setup

1. **Find your Clerk user ID:**
   Go to [Clerk Dashboard](https://dashboard.clerk.com) → **Users** → click your user → copy the **User ID** (format: `user_2x...`).

2. **Set the env var:**
   Add to `.env.local`:
   ```
   ADMIN_USER_IDS=user_abc123
   ```
   For multiple admins, comma-separate:
   ```
   ADMIN_USER_IDS=user_abc123,user_def456
   ```

3. **Fail-closed:** If `ADMIN_USER_IDS` is empty or unset, nobody can access `/admin` — all users are redirected to `/dashboard`.

## Route protection

The `/admin` route is protected by Clerk middleware (it is **not** in the `isPublicRoute` matcher in `middleware.ts`). This means:

- Unauthenticated users are redirected to `/sign-in` by Clerk middleware before the page even loads.
- Authenticated non-admin users are redirected to `/dashboard` by the `requireAdmin()` check.

If your Clerk middleware uses a public-routes allowlist, make sure `/admin` is **not** listed there.

## What it shows

- Total accounts, 7d/30d signups, estimated MRR
- Tier breakdown (Free, Pro trialing, Pro paid, Agency, Expired trial)
- Engagement: active users, avg markets per user, AI scans, alerts sent
- Top 10 tracked cities
- Alerts by urgency (30d)
- Recent 10 account signups
- Recent 10 waitlist signups

All queries run server-side with the Supabase service role key. If any query fails (e.g., the `waitlist` table doesn't exist yet), the page still renders and shows errors in a banner at the top.
