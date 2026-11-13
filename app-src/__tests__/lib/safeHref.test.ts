import { describe, it, expect } from 'vitest'
import { safeHref } from '@/lib/safeHref'

describe('safeHref', () => {
  it('accepts absolute http and https URLs (case-insensitive scheme)', () => {
    expect(safeHref('https://example.gov/page')).toBe('https://example.gov/page')
    expect(safeHref('http://example.gov')).toBe('http://example.gov')
    expect(safeHref('HTTPS://example.gov')).toBe('HTTPS://example.gov')
    expect(safeHref('  https://example.gov  ')).toBe('https://example.gov')
  })

  it('rejects other schemes, relative paths and non-strings', () => {
    expect(safeHref('javascript:alert(1)')).toBeNull()
    expect(safeHref('data:text/html,hi')).toBeNull()
    expect(safeHref('//example.gov')).toBeNull()
    expect(safeHref('/dashboard')).toBeNull()
    expect(safeHref('example.gov')).toBeNull()
    expect(safeHref('')).toBeNull()
    expect(safeHref(null)).toBeNull()
    expect(safeHref(undefined)).toBeNull()
    expect(safeHref(42)).toBeNull()
  })
})
