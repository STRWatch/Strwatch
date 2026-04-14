import { requireAdmin } from '@/lib/admin'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

type TierRow = { user_id: string; tier: string; trial_ends_at: string | null; created_at?: string }
type MarketRow = { user_id: string; city: string }
type AlertRow = { urgency: string }
type ScanRow = { is_enriched: boolean }
type WaitlistRow = { email: string; created_at: string }

function classifyTier(row: TierRow): string {
  if (row.tier === 'agency') return 'agency'
  if (row.tier === 'pro') {
    if (!row.trial_ends_at) return 'pro_paid'
    return new Date(row.trial_ends_at) > new Date() ? 'pro_trialing' : 'expired_trial'
  }
  return 'free'
}

export default async function AdminPage() {
  await requireAdmin()
  const supabase = createClient()

  const errors: string[] = []
  const thirtyDaysAgo = new Date(Date.now() - 30 * 86400000).toISOString()
  const sevenDaysAgo = new Date(Date.now() - 7 * 86400000).toISOString()

  const [tierRes, marketRes, waitlistRes, alertRes, scanRes, recentTierRes, recentWaitlistRes] = await Promise.all([
    supabase.from('user_tiers').select('user_id, tier, trial_ends_at, created_at'),
    supabase.from('user_markets').select('user_id, city'),
    supabase.from('waitlist').select('email, created_at'),
    supabase.from('alerts').select('urgency, sent_at').gte('sent_at', thirtyDaysAgo),
    supabase.from('scans').select('is_enriched'),
    supabase.from('user_tiers').select('user_id, tier, trial_ends_at, created_at').order('created_at', { ascending: false }).limit(10),
    supabase.from('waitlist').select('email, created_at').order('created_at', { ascending: false }).limit(10),
  ])

  if (tierRes.error) errors.push(`user_tiers: ${tierRes.error.message}`)
  if (marketRes.error) errors.push(`user_markets: ${marketRes.error.message}`)
  if (waitlistRes.error) errors.push(`waitlist: ${waitlistRes.error.message}`)
  if (alertRes.error) errors.push(`alerts: ${alertRes.error.message}`)
  if (scanRes.error) errors.push(`scans: ${scanRes.error.message}`)
  if (recentTierRes.error) errors.push(`recent user_tiers: ${recentTierRes.error.message}`)
  if (recentWaitlistRes.error) errors.push(`recent waitlist: ${recentWaitlistRes.error.message}`)

  const tiers = (tierRes.data || []) as TierRow[]
  const markets = (marketRes.data || []) as MarketRow[]
  const waitlist = (waitlistRes.data || []) as WaitlistRow[]
  const alerts = (alertRes.data || []) as (AlertRow & { sent_at: string })[]
  const scans = (scanRes.data || []) as ScanRow[]
  const recentTiers = (recentTierRes.data || []) as TierRow[]
  const recentWaitlist = (recentWaitlistRes.data || []) as WaitlistRow[]

  // ── Tier classification ────────────────────────────────
  const classified = tiers.map(t => ({ ...t, classification: classifyTier(t) }))
  const totalAccounts = tiers.length
  const counts: Record<string, number> = { free: 0, pro_trialing: 0, pro_paid: 0, agency: 0, expired_trial: 0 }
  for (const c of classified) counts[c.classification] = (counts[c.classification] || 0) + 1

  const signups7d = tiers.filter(t => t.created_at && t.created_at >= sevenDaysAgo).length
  const signups30d = tiers.filter(t => t.created_at && t.created_at >= thirtyDaysAgo).length
  const mrr = counts.pro_paid * 29 + counts.agency * 99

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
          <div style={bigNum}>{waitlistTotal}</div>
          <div style={label}>Waitlist total</div>
        </div>
        <div style={card}>
          <div style={bigNum}>{waitlist7d}</div>
          <div style={label}>Waitlist (7d)</div>
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

      {/* ── Recent account signups ─────────────────────── */}
      <div style={{ ...card, marginBottom: '32px', padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1.5px solid #e2e8f0' }}>
          <div style={sectionTitle}>Recent Account Signups</div>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={th}>User ID</th>
                <th style={th}>Tier</th>
                <th style={th}>Trial ends</th>
                <th style={th}>Created</th>
              </tr>
            </thead>
            <tbody>
              {recentTiers.length === 0 ? (
                <tr><td colSpan={4} style={{ ...td, textAlign: 'center', color: '#94a3b8' }}>No data</td></tr>
              ) : recentTiers.map((t, i) => (
                <tr key={i}>
                  <td style={td} title={t.user_id}>{t.user_id.slice(0, 12)}...</td>
                  <td style={td}>{t.tier}</td>
                  <td style={td}>{t.trial_ends_at ? new Date(t.trial_ends_at).toLocaleDateString() : '—'}</td>
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
