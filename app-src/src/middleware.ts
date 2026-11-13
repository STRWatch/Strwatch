import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'
import { PUBLIC_ROUTES } from '@/lib/publicRoutes'

// /api/cron(.*) is public here but guarded by CRON_SECRET in lib/cron.ts.
const isPublicRoute = createRouteMatcher(PUBLIC_ROUTES)

export default clerkMiddleware(async (auth, request) => {
  if (!isPublicRoute(request)) {
    await auth.protect()
  }
})

export const config = {
  matcher: ['/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)', '/(api|trpc)(.*)'],
}
