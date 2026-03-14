'use client'

import { useState, useTransition } from 'react'
import { addMarket, removeMarket } from './actions'

const AVAILABLE_MARKETS = [
  { city: 'Nashville, TN', description: 'Active council monitoring · Legistar API' },
  { city: 'Austin, TX',    description: 'July 1 enforcement deadline · 2,744 licenses tracked' },
  { city: 'Denver, CO',    description: '7,449 licenses tracked · SODA API' },
  { city: 'Scottsdale, AZ', description: '2,999 licenses tracked · ArcGIS API' },
  { city: 'Palm Springs, CA', description: 'PrimeGov council portal · Active enforcement' },
]

export default function MarketsClient({
  userId,
  savedCities,
}: {
  userId: string
  savedCities: string[]
}) {
  const [cities, setCities] = useState<string[]>(savedCities)
  const [isPending, startTransition] = useTransition()
  const [feedback, setFeedback] = useState<{ city: string; msg: string } | null>(null)

  function showFeedback(city: string, msg: string) {
    setFeedback({ city, msg })
    setTimeout(() => setFeedback(null), 2500)
  }

  function handleAdd(city: string) {
    if (cities.includes(city)) return
    setCities(prev => [...prev, city])
    startTransition(async () => {
      const res = await addMarket(userId, city)
      if (!res.ok) {
        setCities(prev => prev.filter(c => c !== city))
        showFeedback(city, 'Failed to add — try again')
      } else {
        showFeedback(city, 'Added ✓')
      }
    })
  }

  function handleRemove(city: string) {
    setCities(prev => prev.filter(c => c !== city))
    startTransition(async () => {
      const res = await removeMarket(userId, city)
      if (!res.ok) {
        setCities(prev => [...prev, city])
        showFeedback(city, 'Failed to remove — try again')
      } else {
        showFeedback(city, 'Removed')
      }
    })
  }

  return (
    <div>
      <h1 style={{ fontFamily: 'var(--font-syne)', fontWeight: 800, fontSize: '1.6rem', color: 'var(--ink)', marginBottom: '0.4rem', letterSpacing: '-0.02em' }}>
        Your Markets
      </h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: '2rem', fontSize: '0.9rem' }}>
        Select the cities where you have properties. You'll receive alerts when regulations change in these markets.
      </p>

      {/* Active markets */}
      {cities.length > 0 && (
        <div style={{ marginBottom: '2rem' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6rem', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: '0.75rem' }}>
            Tracking {cities.length} market{cities.length !== 1 ? 's' : ''}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {cities.map(city => (
              <div key={city} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--green-pale)', border: '1.5px solid var(--green-light)', borderRadius: '10px', padding: '14px 18px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ width: '8px', height: '8px', background: 'var(--green-bright)', borderRadius: '50%', animation: 'pulse 2s ease-in-out infinite' }} />
                  <span style={{ fontFamily: 'var(--font-syne)', fontWeight: 600, fontSize: '0.9rem', color: 'var(--ink)' }}>{city}</span>
                  {feedback?.city === city && (
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6rem', color: 'var(--green)', letterSpacing: '0.05em' }}>{feedback.msg}</span>
                  )}
                </div>
                <button
                  onClick={() => handleRemove(city)}
                  disabled={isPending}
                  style={{ fontFamily: 'var(--font-mono)', fontSize: '0.58rem', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-faint)', background: 'none', border: 'none', cursor: 'pointer', padding: '4px 8px' }}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Available markets */}
      <div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6rem', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: '0.75rem' }}>
          Available markets — beta
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {AVAILABLE_MARKETS.map(({ city, description }) => {
            const active = cities.includes(city)
            return (
              <div key={city} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'white', border: `1.5px solid ${active ? 'var(--green-light)' : 'var(--border)'}`, borderRadius: '10px', padding: '14px 18px', opacity: active ? 0.5 : 1 }}>
                <div>
                  <div style={{ fontFamily: 'var(--font-syne)', fontWeight: 600, fontSize: '0.9rem', color: 'var(--ink)', marginBottom: '2px' }}>{city}</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.58rem', color: 'var(--text-faint)', letterSpacing: '0.05em' }}>{description}</div>
                </div>
                <button
                  onClick={() => handleAdd(city)}
                  disabled={active || isPending}
                  style={{
                    fontFamily: 'var(--font-syne)', fontWeight: 700, fontSize: '0.75rem',
                    padding: '8px 18px', borderRadius: '6px', border: 'none', cursor: active ? 'default' : 'pointer',
                    background: active ? 'var(--border)' : 'var(--green-deep)', color: active ? 'var(--text-faint)' : 'white',
                    transition: 'background 0.2s', whiteSpace: 'nowrap',
                  }}
                >
                  {active ? 'Added' : 'Add market'}
                </button>
              </div>
            )
          })}
        </div>
      </div>

      {cities.length === 0 && (
        <div style={{ marginTop: '2rem', padding: '20px', background: 'var(--off-white)', border: '1px solid var(--border)', borderRadius: '10px', textAlign: 'center' }}>
          <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', letterSpacing: '0.08em', color: 'var(--text-faint)' }}>
            No markets added yet — add a city above to start receiving alerts
          </p>
        </div>
      )}
    </div>
  )
}
