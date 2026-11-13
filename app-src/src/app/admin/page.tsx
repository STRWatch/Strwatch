import { requireAdmin } from '@/lib/admin'
import { createClient } from '@/lib/supabase/server'
import { clerkClient } from '@clerk/nextjs/server'

export const dynamic = 'force-dynamic'

type TierRow = {
  user_id: string
  tier: string
  trial_ends_at: string | null
  created_at?: string | null
  stripe_customer_id?: string | null
  founding_member?: boolean | null
  last_login_at?: string | null
}
type MarketRow = { user_id: string; city: string }
type AlertRow = { urgency: string }
type ScanRow = { is_enriched: boolean }
type WaitlistRow = { email: string; created_at: string }
type ScrapeRunRow = {
  source: string
  city: string
  status: string
  started_at: string
  finished_at: string | null
  pages_changed: number | null
  error: string | null
}

const STALE_HOURS = 48

function classifyTier(row: TierRow): string {
  if (row.tier === 'agency') return 'agency'
  if (row.tier === 'pro') {
    if (!row.trial_ends_at) return 'pro_paid'
    return new Date(row.trial_ends_at) > new Date() ? 'pro_trialing' : 'expired_trial'
  }
  return 'free'
}

type EffectiveTierKey = 'free' | 'trial' | 'pro' | 'agency'

/** Mirrors getEffectiveTier: an expired, unpaid 'pro' trial reads as free. */
function effectiveTier(row: TierRow, now: Date): EffectiveTierKey {
  if (row.tier === 'agency') return 'agency'
  if (row.tier !== 'pro') return 'free'
  if (!row.trial_ends_at) return 'pro'
  return new Date(row.trial_ends_at) > now ? 'trial' : 'free'
}

/** ISO-8601 week key (e.g. 2026-W46) for a date, computed in UTC. */
function isoWeekKey(d: Date): string {
  const date = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()))
  const day = date.getUTCDay() || 7
  date.setUTCDate(date.getUTCDate() + 4 - day)
  const yearStart = Date.UTC(date.getUTCFullYear(), 0, 1)
  const week = Math.ceil(((date.getTime() - yearStart) / 86400000 + 1) / 7)
  return `${date.getUTCFullYear()}-W${String(week).padStart(2, '0')}`
}

const TIER_SELECT = 'user_id, tier, trial_ends_at, created_at, stripe_customer_id, founding_member, last_login_at'

export default async function AdminPage() {
  await requireAdmin()
  const supabase = createClient()

  const errors: string[] = []
  const thirtyDaysAgo = new Date(Date.now() - 30 * 86400000).toISOString()
  const sevenDaysAgo = new Date(Date.now() - 7 * 86400000).toISOString()

  const [tierRes, marketRes, waitlistRes, alertRes, scanRes, recentWaitlistRes, scrapeRunsRes] = await Promise.all([
    supabase.from('user_tiers').select(TIER_SELECT),
    supabase.from('user_markets').select('user_id, city'),
    supabase.from('waitlist').select('email, created_at'),
    supabase.from('alerts').select('urgency, sent_at').gte('sent_at', thirtyDaysAgo),
    supabase.from('scans').select('is_enriched'),
    supabase.from('waitlist').select('email, created_at').order('created_at', { ascending: false }).limit(10),
    supabase.from('scrape_runs').select('source, city, status, started_at, finished_at, pages_changed, error').order('started_at', { ascending: false }).limit(2000),
  ])

  if (tierRes.error) errors.push(`user_tiers: ${tierRes.error.message}`)
  if (marketRes.error) errors.push(`user_markets: ${marketRes.error.message}`)
  if (waitlistRes.error) errors.push(`waitlist: ${waitlistRes.error.message}`)
  if (alertRes.error) errors.push(`alerts: ${alertRes.error.message}`)
  if (scanRes.error) errors.push(`scans: ${scanRes.error.message}`)
  if (recentWaitlistRes.error) errors.push(`recent waitlist: ${recentWaitlistRes.error.message}`)
  if (scrapeRunsRes.error) errors.push(`scrape_runs: ${scrapeRunsRes.error.message}`)

  const tiers = (tierRes.data || []) as TierRow[]
  const markets = (marketRes.data || []) as MarketRow[]
  const waitlist = (waitlistRes.data || []) as WaitlistRow[]
  const alerts = (alertRes.data || []) as (AlertRow & { sent_at: string })[]
  const scans = (scanRes.data || []) as ScanRow[]
  const recentWaitlist = (recentWaitlistRes.data || []) as WaitlistRow[]
  const scrapeRuns = (scrapeRunsRes.data || []) as ScrapeRunRow[]

  // ── Resolve emails from Clerk (all accounts, batches of 100) ───
  const emailMap: Record<string, string> = {}
  const allUserIds = Array.from(new Set(tiers.map(t => t.user_id).filter(Boolean)))
  if (allUserIds.length > 0) {
    try {
      const clerk = await clerkClient()
      for (let i = 0; i < allUserIds.length; i += 100) {
        const batch = allUserIds.slice(i, i + 100)
        const res = await clerk.users.getUserList({ userId: batch, limit: 100 })
        for (const u of res.data) {
          emailMap[u.id] = u.emailAddresses?.[0]?.emailAddress || ''
        }
      }
    } catch (e: any) {
      errors.push(`Clerk user lookup: ${e.message}`)
    }
  }

  // ── Tier classification ────────────────────────────────
  const classified = tiers.map(t => ({ ...t, classification: classifyTier(t) }))
  const totalAccounts = tiers.length
  const counts: Record<string, number> = { free: 0, pro_trialing: 0, pro_paid: 0, agency: 0, expired_trial: 0 }
  for (const c of classified) counts[c.classification] = (counts[c.classification] || 0) + 1

  const signups7d = tiers.filter(t => t.created_at && t.created_at >= sevenDaysAgo).length
  const signups30d = tiers.filter(t => t.created_at && t.created_at >= thirtyDaysAgo).length
  const mrr = counts.pro_paid * 29 + counts.agency * 99

  // ── Effective tier counts (same logic as getEffectiveTier) ──
  const now = new Date()
  const effectiveCounts: Record<EffectiveTierKey, number> = { free: 0, trial: 0, pro: 0, agency: 0 }
  for (const t of tiers) effectiveCounts[effectiveTier(t, now)]++

  // ── Trial-to-paid conversion ───────────────────────────
  const paidUsers = tiers.filter(t => !!t.stripe_customer_id).length
  const endedTrials = tiers.filter(t => t.trial_ends_at && new Date(t.trial_ends_at) < now).length
  const conversionPct = endedTrials > 0 ? ((paidUsers / endedTrials) * 100).toFixed(1) : null

  // ── Signups per ISO week, last 12 weeks ────────────────
  const weekKeys: string[] = []
  for (let i = 11; i >= 0; i--) weekKeys.push(isoWeekKey(new Date(now.getTime() - i * 7 * 86400000)))
  const weekCounts: Record<string, number> = Object.fromEntries(weekKeys.map(k => [k, 0]))
  for (const t of tiers) {
    if (!t.created_at) continue
    const k = isoWeekKey(new Date(t.created_at))
    if (k in weekCounts) weekCounts[k]++
  }
  const weeklySignups = weekKeys.map(k => [k, weekCounts[k]] as const)

  // ── Scraper health: latest run per (source, city) ──────
  // Rows arrive ordered by started_at desc, so the first hit per key is the latest.
  const latestRuns = new Map<string, ScrapeRunRow>()
  for (const r of scrapeRuns) {
    const key = `${r.source}\u0000${r.city}`
    if (!latestRuns.has(key)) latestRuns.set(key, r)
  }
  const hoursSince = (r: ScrapeRunRow): number | null => {
    const ts = r.finished_at || r.started_at
    return ts ? (now.getTime() - new Date(ts).getTime()) / 3600000 : null
  }
  const isError = (r: ScrapeRunRow) => r.status === 'error'
  const isStale = (r: ScrapeRunRow) => {
    const h = hoursSince(r)
    return h === null || h > STALE_HOURS
  }
  const rank = (r: ScrapeRunRow) => (isError(r) ? 0 : isStale(r) ? 1 : 2)
  const healthRows = Array.from(latestRuns.values()).sort((a, b) => {
    const d = rank(a) - rank(b)
    if (d !== 0) return d
    return a.source.localeCompare(b.source) || a.city.localeCompare(b.city)
  })
  const healthErrors = healthRows.filter(isError).length
  const healthStale = healthRows.filter(r => !isError(r) && isStale(r)).length

  // ── Users table ────────────────────────────────────────
  const marketCountByUser: Record<string, number> = {}
  for (const m of markets) marketCountByUser[m.user_id] = (marketCountByUser[m.user_id] || 0) + 1
  const userRows = [...tiers].sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))

  // ── Waitlist stats ─────────────────────────────────────
  const waitlistTotal = waitlist.length
  const waitlist7d = waitlist.filter(w => w.created_at >= sevenDaysAgo).length

  // ── Engagement ─────────────────────────────────────────
  const activeUserIds = new Set(markets.map(m => m.user_id))
  const activeUsers = activeUserIds.size
  const avgMarkets = activeUsers > 0 ? (markets.length / activeUsers).toFixed(1) : '0'
  const totalScans = scans.length
  const enrichedScans = scans.filter(s => s.is_enriched).length
  const alertsSent30d = alerts.length

  // ── Top cities ─────────────────────────────────────────
  const cityMap: Record<string, number> = {}
  for (const m of markets) cityMap[m.city] = (cityMap[m.city] || 0) + 1
  const topCities = Object.entries(cityMap).sort((a, b) => b[1] - a[1]).slice(0, 10)

  // ── Alerts by urgency ──────────────────────────────────
  const urgencyMap: Record<string, number> = {}
  for (const a of alerts) urgencyMap[a.urgency] = (urgencyMap[a.urgency] || 0) + 1
  const urgencySorted = Object.entries(urgencyMap).sort((a, b) => b[1] - a[1])

  const URGENCY_PILL: Record<string, { bg: string; border: string; text: string }> = {
    critical: { bg: '#fff0ee', border: '#f7c8c8', text: '#b84040' },
    high:     { bg: '#fff0ee', border: '#f7c8c8', text: '#b84040' },
    medium:   { bg: '#fdf3e3', border: '#f5d9a0', text: '#b87d2d' },
    low:      { bg: '#e8f0ff', border: '#b8cff7', text: '#3060a8' },
  }

  const EFFECTIVE_LABELS: Record<EffectiveTierKey, string> = { free: 'Free', trial: 'Trial', pro: 'Pro', agency: 'Agency' }

  const TIER_LABELS: Record<string, string> = {
    free: 'Free',
    pro_trialing: 'Pro (trialing)',
    pro_paid: 'Pro (paid)',
    agency: 'Agency',
    expired_trial: 'Expired trial',
  }

  // ── Styles ─────────────────────────────────────────────
  const card: React.CSSProperties = {
    background: '#fff',
    border: '1.5px solid #e2e8f0',
    borderRadius: '12px',
    padding: '20px',
  }
  const sectionTitle: React.CSSProperties = {
    fontFamily: 'var(--font-syne)',
    fontWeight: 700,
    fontSize: '0.95rem',
    color: '#0f172a',
    marginBottom: '16px',
  }
  const label: React.CSSProperties = {
    fontSize: '0.7rem',
    color: '#64748b',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.1em',
  }
  const bigNum: React.CSSProperties = {
    fontSize: '2rem',
    fontWeight: 800,
    color: '#0f172a',
    lineHeight: 1,
    marginBottom: '8px',
  }
  const th: React.CSSProperties = {
    textAlign: 'left' as const,
    padding: '8px 12px',
    fontSize: '0.65rem',
    color: '#64748b',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.08em',
    borderBottom: '1.5px solid #e2e8f0',
  }
  const td: React.CSSProperties = {
    padding: '10px 12px',
    fontSize: '0.8rem',
    color: '#334155',
    borderBottom: '1px solid #f1f5f9',
    fontFamily: 'monospace',
  }

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '32px 24px' }}>
      <h1 style={{ fontFamily: 'var(--font-syne)', fontWeight: 800, fontSize: '1.6rem', color: '#0f172a', marginBottom: '4px', letterSpacing: '-0.02em' }}>
        Admin Dashboard
      </h1>
      <p style={{ fontSize: '0.875rem', color: '#64748b', marginBottom: '32px' }}>
        Account &amp; usage metrics across STRWatch.
      </p>

      {/* Error banner */}
      {errors.length > 0 && (
        <div style={{ marginBottom: '24px', padding: '12px 16px', background: '#fff0ee', border: '1.5px solid #f7c8c8', borderRadius: '8px' }}>
          <div style={{ fontFamily: 'monospace', fontSize: '0.7rem', color: '#b84040', fontWeight: 700, marginBottom: '4px' }}>Query errors</div>
          {errors.map((e, i) => (
            <div key={i} style={{ fontFamily: 'monospace', fontSize: '0.65rem', color: '#b84040' }}>{e}</div>
          ))}
        </div>
      )}

      {/* ── Top stat cards ──────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '16px', marginBottom: '32px' }}>
        <div style={card}>
          <div style={bigNum}>{totalAccounts}</div>
          <div style={label}>Total accounts</div>
        </div>
        <div style={card}>
          <div style={bigNum}>{signups7d}</div>
          <div style={label}>Signups (7d)</div>
        </div>
        <div style={card}>
          <div style={bigNum}>{signups30d}</div>
          <div style={label}>Signups (30d)</div>
        </div>
        <div style={card}>
          <div style={bigNum}>${mrr.toLocaleString()}</div>
          <div style={label}>Est. MRR</div>
        </div>
        <div style={card}>
          <div style={bigNum}>{conversionPct !== null ? `${conversionPct}%` : '—'}</div>
          <div style={label}>Trial → paid</div>
          <div style={{ fontSize: '0.6rem', color: '#94a3b8', marginTop: '4px' }}>{paidUsers} paid / {endedTrials} trials ended</div>
        </div>
        <div style={card}>
          <div style={bigNum}>{waitlistTotal}</div>
          <div style={label}>Waitlist total</div>
        </div>
        <div style={card}>
          <div style={bigNum}>{waitlist7d}</div>
          <div style={label}>Waitlist (7d)</div>
        </div>
      </div>

      {/* ── Effective tier + weekly signups ───────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px', marginBottom: '32px' }}>
        <div style={card}>
          <div style={sectionTitle}>Current Users by Effective Tier</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))', gap: '12px' }}>
            {(Object.keys(EFFECTIVE_LABELS) as EffectiveTierKey[]).map(key => (
              <div key={key} style={{ padding: '14px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#0f172a', lineHeight: 1, marginBottom: '4px' }}>{effectiveCounts[key]}</div>
                <div style={{ fontSize: '0.65rem', color: '#64748b' }}>{EFFECTIVE_LABELS[key]}</div>
              </div>
            ))}
          </div>
          <div style={{ fontSize: '0.6rem', color: '#94a3b8', marginTop: '10px' }}>Expired, unpaid Pro trials count as Free (same rule as getEffectiveTier).</div>
        </div>
        <div style={card}>
          <div style={sectionTitle}>Signups per ISO Week (last 12)</div>
          {weeklySignups.map(([week, count], i) => (
            <div key={week} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '5px 0', borderBottom: i < weeklySignups.length - 1 ? '1px solid #f1f5f9' : 'none' }}>
              <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#334155' }}>{week}</span>
              <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>{count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Tier breakdown ─────────────────────────────── */}
      <div style={{ ...card, marginBottom: '32px' }}>
        <div style={sectionTitle}>Tier Breakdown</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px' }}>
          {Object.entries(TIER_LABELS).map(([key, name]) => {
            const count = counts[key] || 0
            const pct = totalAccounts > 0 ? ((count / totalAccounts) * 100).toFixed(1) : '0.0'
            return (
              <div key={key} style={{ padding: '14px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#0f172a', lineHeight: 1, marginBottom: '4px' }}>{count}</div>
                <div style={{ fontSize: '0.65rem', color: '#64748b' }}>{name}</div>
                <div style={{ fontSize: '0.6rem', color: '#94a3b8', marginTop: '2px' }}>{pct}%</div>
              </div>
            )
          })}
        </div>
      </div>

      {/* ── Engagement ─────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', marginBottom: '32px' }}>
        <div style={card}>
          <div style={bigNum}>{activeUsers}</div>
          <div style={label}>Active users</div>
          <div style={{ fontSize: '0.6rem', color: '#94a3b8', marginTop: '4px' }}>Distinct users with markets</div>
        </div>
        <div style={card}>
          <div style={bigNum}>{avgMarkets}</div>
          <div style={label}>Avg markets / user</div>
        </div>
        <div style={card}>
          <div style={bigNum}>{totalScans}</div>
          <div style={label}>Total AI scans</div>
          <div style={{ fontSize: '0.6rem', color: '#94a3b8', marginTop: '4px' }}>{enrichedScans} enriched</div>
        </div>
        <div style={card}>
          <div style={bigNum}>{alertsSent30d}</div>
          <div style={label}>Alerts sent (30d)</div>
        </div>
      </div>

      {/* ── Top cities + Alerts by urgency ─────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px', marginBottom: '32px' }}>
        {/* Top cities */}
        <div style={card}>
          <div style={sectionTitle}>Top 10 Tracked Cities</div>
          {topCities.length === 0 ? (
            <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>No data</div>
          ) : topCities.map(([city, count], i) => (
            <div key={city} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: i < topCities.length - 1 ? '1px solid #f1f5f9' : 'none' }}>
              <span style={{ fontSize: '0.8rem', color: '#334155' }}>{city}</span>
              <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>{count}</span>
            </div>
          ))}
        </div>

        {/* Alerts by urgency */}
        <div style={card}>
          <div style={sectionTitle}>Alerts by Urgency (30d)</div>
          {urgencySorted.length === 0 ? (
            <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>No alerts in last 30 days</div>
          ) : urgencySorted.map(([urg, count]) => {
            const pill = URGENCY_PILL[urg] || URGENCY_PILL.medium
            return (
              <div key={urg} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f1f5f9' }}>
                <span style={{
                  display: 'inline-block', background: pill.bg, border: `1px solid ${pill.border}`, color: pill.text,
                  fontSize: '0.6rem', letterSpacing: '0.08em', textTransform: 'uppercase', padding: '3px 10px', borderRadius: '100px',
                }}>{urg}</span>
                <span style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: '#334155', fontWeight: 600 }}>{count}</span>
              </div>
            )
          })}
        </div>
      </div>

      {/* ── Scraper health ─────────────────────────────── */}
      <div style={{ ...card, marginBottom: '32px', padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1.5px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ ...sectionTitle, marginBottom: 0 }}>Scraper Health</div>
          <div style={{ fontFamily: 'monospace', fontSize: '0.7rem', color: '#64748b' }}>
            {healthRows.length} sources · <span style={{ color: healthErrors > 0 ? '#b84040' : '#64748b' }}>{healthErrors} errors</span> · <span style={{ color: healthStale > 0 ? '#b87d2d' : '#64748b' }}>{healthStale} stale (&gt;{STALE_HOURS}h)</span>
          </div>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={th}>Source</th>
                <th style={th}>City</th>
                <th style={th}>Status</th>
                <th style={th}>Finished</th>
                <th style={th}>Hours since</th>
                <th style={th}>Pages changed</th>
                <th style={th}>Error</th>
              </tr>
            </thead>
            <tbody>
              {healthRows.length === 0 ? (
                <tr><td colSpan={7} style={{ ...td, textAlign: 'center', color: '#94a3b8' }}>No scrape runs recorded</td></tr>
              ) : healthRows.map(r => {
                const h = hoursSince(r)
                const err = isError(r)
                const stale = !err && isStale(r)
                const statusColor = err ? '#b84040' : stale ? '#b87d2d' : r.status === 'changed' ? '#3060a8' : '#2d7a4f'
                const errText = r.error ? (r.error.length > 120 ? `${r.error.slice(0, 120)}…` : r.error) : '—'
                return (
                  <tr key={`${r.source}|${r.city}`} style={{ background: err ? '#fff7f6' : stale ? '#fffbf2' : undefined }}>
                    <td style={td}>{r.source}</td>
                    <td style={td}>{r.city}</td>
                    <td style={{ ...td, color: statusColor, fontWeight: 600 }}>{r.status}{stale ? ' (stale)' : ''}</td>
                    <td style={td}>{r.finished_at ? new Date(r.finished_at).toLocaleString() : '—'}</td>
                    <td style={td}>{h === null ? '—' : h.toFixed(1)}</td>
                    <td style={td}>{r.pages_changed ?? '—'}</td>
                    <td style={{ ...td, maxWidth: '360px', whiteSpace: 'normal', wordBreak: 'break-word' }} title={r.error || undefined}>{errText}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Users ──────────────────────────────────────── */}
      <div style={{ ...card, marginBottom: '32px', padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1.5px solid #e2e8f0' }}>
          <div style={sectionTitle}>Users ({userRows.length})</div>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={th}>Email</th>
                <th style={th}>Tier</th>
                <th style={th}>Trial ends</th>
                <th style={th}>Founding</th>
                <th style={th}>Markets</th>
                <th style={th}>Last login</th>
                <th style={th}>Created</th>
              </tr>
            </thead>
            <tbody>
              {userRows.length === 0 ? (
                <tr><td colSpan={7} style={{ ...td, textAlign: 'center', color: '#94a3b8' }}>No data</td></tr>
              ) : userRows.map(t => (
                <tr key={t.user_id}>
                  <td style={td} title={t.user_id}>{emailMap[t.user_id] || `${t.user_id.slice(0, 12)}...`}</td>
                  <td style={td}>{EFFECTIVE_LABELS[effectiveTier(t, now)]}</td>
                  <td style={td}>{t.trial_ends_at ? new Date(t.trial_ends_at).toLocaleDateString() : '—'}</td>
                  <td style={td}>{t.founding_member ? 'yes' : '—'}</td>
                  <td style={td}>{marketCountByUser[t.user_id] || 0}</td>
                  <td style={td}>{t.last_login_at ? new Date(t.last_login_at).toLocaleString() : '—'}</td>
                  <td style={td}>{t.created_at ? new Date(t.created_at).toLocaleDateString() : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Recent waitlist signups ────────────────────── */}
      <div style={{ ...card, padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1.5px solid #e2e8f0' }}>
          <div style={sectionTitle}>Recent Waitlist Signups</div>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={th}>Email</th>
                <th style={th}>Created</th>
              </tr>
            </thead>
            <tbody>
              {recentWaitlist.length === 0 ? (
                <tr><td colSpan={2} style={{ ...td, textAlign: 'center', color: '#94a3b8' }}>No data</td></tr>
              ) : recentWaitlist.map((w, i) => (
                <tr key={i}>
                  <td style={td}>{w.email}</td>
                  <td style={td}>{new Date(w.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
