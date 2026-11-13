/** Public origin of the app, no trailing slash. Read per call, never at module load. */
export function appUrl(): string {
  return (process.env.NEXT_PUBLIC_APP_URL || 'https://app.strwatch.io').replace(/\/$/, '')
}
