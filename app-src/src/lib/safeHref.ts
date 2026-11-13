/**
 * Returns the href when it is an absolute http(s) URL, otherwise null.
 * Use before rendering user- or scraper-supplied URLs as <a href>, so
 * javascript:, data: and relative values are shown as plain text instead.
 */
export function safeHref(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const trimmed = value.trim()
  return /^https?:\/\//i.test(trimmed) ? trimmed : null
}
