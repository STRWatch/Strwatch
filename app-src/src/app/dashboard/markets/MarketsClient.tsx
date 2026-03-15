'use client'

import { useState, useTransition } from 'react'
import { addMarket, removeMarket } from './actions'

const AVAILABLE_MARKETS = [
  { city: 'Nashville, TN', description: 'Active council monitoring · Legistar API' },
  { city: 'Austin, TX',    description: 'July 1 enforcement deadline · 2,744 licenses tracked' },
  { city: 'Denver, CO',    description: '7,449 licenses tracked · SODA API' },
  { city: 'Scottsdale, AZ', description: '2,999 licenses tracked · ArcGIS API' },
  { city: 'Palm Springs, CA', description: 'PrimeGov council portal · Active enforcement' },
  { city: 'New Orleans, LA', description: '1,300 licenses tracked · Legistar + SODA API' },
  { city: 'San Diego, CA', description: '7,954 STRO licenses · 4-tier system · Page monitoring' },
  { city: 'Charleston, SC', description: 'Strict zoning overlay · ~700 permits · Page monitoring' },
  { city: 'Savannah, GA', description: 'STVR overlay district · 20% ward cap · Deckard portal' },
  { city: 'San Francisco, CA', description: '$925 app fee · 90-night cap · 14% TOT · Page monitoring' },
  { city: 'Miami Beach, FL', description: '$20K+ fines · Strict zoning · 4 licenses required · Page monitoring' },
  { city: 'Gatlinburg, TN', description: 'Tourist Residency Permit · Massive STR density · Smoky Mountains' },
  { city: 'Asheville, NC', description: 'Whole-home STRs banned in residential · Homestays only · Active enforcement' },
]

export default function MarketsClient({
  userId, savedCities, tier, maxMarkets, trialDaysLeft, isTrialActive, isPaid,
}: {
  userId: string; savedCities: string[]; tier: string; maxMarkets: number;
  trialDaysLeft: number; isTrialActive: boolean; isPaid: boolean;
}) {
  const [cities, setCities] = useState<string[]>(savedCities)
  const [isPending, startTransition] = useTransition()
  const [feedback, setFeedback] = useState<{ city: string; msg: string } | null>(null)
  const isFree = tier === 'free'

  async function handleUpgrade() {
    const res = await fetch('/api/stripe/checkout', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({tier: 'pro'}),
    })
    const data = await res.json()
    if (data.url) window.location.href = data.url
  }
  const atLimit = cities.length >= maxMarkets

  function showFeedback(city: string, msg: string) {
    setFeedback({ city, msg })
    setTimeout(() => setFeedback(null), 3000)
  }

  function handleAdd(city: string) {
    if (cities.includes(city)) return
    if (atLimit) { showFeedback(city, isFree ? 'Upgrade to Pro for unlimited markets' : 'Limit reached'); return }
    setCities(prev => [...prev, city])
    startTransition(async () => {
      const res = await addMarket(userId, city)
      if (!res.ok) { setCities(prev => prev.filter(c => c !== city)); showFeedback(city, 'Failed — try again') }
      else showFeedback(city, 'Added ✓')
    })
  }

  function handleRemove(city: string) {
    if (isFree) { showFeedback(city, 'Free plan: upgrade to change markets'); return }
    setCities(prev => prev.filter(c => c !== city))
    startTransition(async () => {
      const res = await removeMarket(userId, city)
      if (!res.ok) { setCities(prev => [...prev, city]); showFeedback(city, 'Failed — try again') }
    })
  }

  return (
    <div>
      <h1 style={{fontFamily:'var(--font-syne)',fontWeight:800,fontSize:'1.6rem',color:'var(--ink)',marginBottom:'0.4rem',letterSpacing:'-0.02em'}}>Your Markets</h1>
      <p style={{color:'var(--text-muted)',marginBottom:'1rem',fontSize:'0.9rem'}}>
        Select the cities where you have properties. You'll receive alerts when regulations change.
      </p>

      {/* Trial active banner */}
      {isTrialActive && !isPaid && (
        <div style={{marginBottom:'1.5rem',padding:'12px 16px',background:'#e8f5ee',border:'1.5px solid #c8ecd8',borderRadius:'8px',display:'flex',alignItems:'center',justifyContent:'space-between',gap:'12px'}}>
          <span style={{fontFamily:'var(--font-mono)',fontSize:'0.62rem',letterSpacing:'0.08em',color:'#2d7a4f'}}>
            PRO TRIAL · <strong>{trialDaysLeft} day{trialDaysLeft !== 1 ? 's' : ''} remaining</strong> · Unlimited markets & real-time alerts
          </span>
          <button onClick={handleUpgrade} style={{fontFamily:'var(--font-syne)',fontWeight:700,fontSize:'0.72rem',padding:'6px 14px',background:'#1a4d2e',color:'white',borderRadius:'6px',border:'none',cursor:'pointer',whiteSpace:'nowrap'}}>
            Lock $29/mo →
          </button>
        </div>
      )}

      {/* Free tier banner (trial expired or never had trial) */}
      {isFree && (
        <div style={{marginBottom:'1.5rem',padding:'12px 16px',background:'#fdf3e3',border:'1.5px solid #f5d9a0',borderRadius:'8px',display:'flex',alignItems:'center',justifyContent:'space-between',gap:'12px'}}>
          <span style={{fontFamily:'var(--font-mono)',fontSize:'0.62rem',letterSpacing:'0.08em',color:'#b87d2d'}}>
            FREE PLAN · 1 market max · <strong>Upgrade to Pro</strong> for unlimited markets + real-time alerts
          </span>
          <button onClick={handleUpgrade} style={{fontFamily:'var(--font-syne)',fontWeight:700,fontSize:'0.72rem',padding:'6px 14px',background:'#1a4d2e',color:'white',borderRadius:'6px',border:'none',cursor:'pointer',whiteSpace:'nowrap'}}>
            Upgrade — $29/mo →
          </button>
        </div>
      )}

      {cities.length > 0 && (
        <div style={{marginBottom:'2rem'}}>
          <div style={{fontFamily:'var(--font-mono)',fontSize:'0.6rem',letterSpacing:'0.15em',textTransform:'uppercase',color:'var(--text-faint)',marginBottom:'0.75rem'}}>
            Tracking {cities.length} market{cities.length !== 1 ? 's' : ''}
          </div>
          <div style={{display:'flex',flexDirection:'column',gap:'8px'}}>
            {cities.map(city => (
              <div key={city} style={{display:'flex',alignItems:'center',justifyContent:'space-between',background:'var(--green-pale)',border:'1.5px solid var(--green-light)',borderRadius:'10px',padding:'14px 18px'}}>
                <div style={{display:'flex',alignItems:'center',gap:'10px'}}>
                  <div style={{width:'8px',height:'8px',background:'var(--green-bright)',borderRadius:'50%'}} />
                  <span style={{fontFamily:'var(--font-syne)',fontWeight:600,fontSize:'0.9rem',color:'var(--ink)'}}>{city}</span>
                  {feedback?.city === city && <span style={{fontFamily:'var(--font-mono)',fontSize:'0.6rem',color:feedback.msg.includes('Upgrade') ? '#b87d2d' : 'var(--green)',letterSpacing:'0.05em'}}>{feedback.msg}</span>}
                </div>
                <button onClick={() => handleRemove(city)} disabled={isPending}
                  style={{fontFamily:'var(--font-mono)',fontSize:'0.58rem',letterSpacing:'0.1em',textTransform:'uppercase',color:'var(--text-faint)',background:'none',border:'none',cursor:isFree ? 'not-allowed' : 'pointer',padding:'4px 8px',opacity:isFree ? 0.5 : 1}}
                  title={isFree ? 'Upgrade to change markets' : 'Remove market'}>
                  {isFree ? 'Locked' : 'Remove'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <div style={{fontFamily:'var(--font-mono)',fontSize:'0.6rem',letterSpacing:'0.15em',textTransform:'uppercase',color:'var(--text-faint)',marginBottom:'0.75rem'}}>
          Available markets — beta
        </div>
        <div style={{display:'flex',flexDirection:'column',gap:'8px'}}>
          {AVAILABLE_MARKETS.map(({ city, description }) => {
            const active = cities.includes(city)
            const disabled = active || (atLimit && !active)
            return (
              <div key={city} style={{display:'flex',alignItems:'center',justifyContent:'space-between',background:'white',border:`1.5px solid ${active ? 'var(--green-light)' : 'var(--border)'}`,borderRadius:'10px',padding:'14px 18px',opacity:active ? 0.5 : 1}}>
                <div>
                  <div style={{fontFamily:'var(--font-syne)',fontWeight:600,fontSize:'0.9rem',color:'var(--ink)',marginBottom:'2px'}}>{city}</div>
                  <div style={{fontFamily:'var(--font-mono)',fontSize:'0.58rem',color:'var(--text-faint)',letterSpacing:'0.05em'}}>{description}</div>
                  {feedback?.city === city && !active && <div style={{fontFamily:'var(--font-mono)',fontSize:'0.6rem',color:'#b87d2d',marginTop:'4px'}}>{feedback.msg}</div>}
                </div>
                <button onClick={() => handleAdd(city)} disabled={disabled || isPending}
                  style={{fontFamily:'var(--font-syne)',fontWeight:700,fontSize:'0.75rem',padding:'8px 18px',borderRadius:'6px',border:'none',cursor:disabled ? 'default' : 'pointer',background:active ? 'var(--border)' : atLimit ? '#f5d9a0' : 'var(--green-deep)',color:active ? 'var(--text-faint)' : atLimit ? '#b87d2d' : 'white',whiteSpace:'nowrap'}}>
                  {active ? 'Added' : atLimit && isFree ? 'Upgrade' : 'Add market'}
                </button>
              </div>
            )
          })}
        </div>
      </div>

      {cities.length === 0 && (
        <div style={{marginTop:'2rem',padding:'20px',background:'var(--off-white)',border:'1px solid var(--border)',borderRadius:'10px',textAlign:'center'}}>
          <p style={{fontFamily:'var(--font-mono)',fontSize:'0.65rem',letterSpacing:'0.08em',color:'var(--text-faint)'}}>No markets added yet — add a city above to start receiving alerts</p>
        </div>
      )}
    </div>
  )
}
