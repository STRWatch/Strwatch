'use client'

import { useState, useTransition, useRef, useEffect } from 'react'
import { addMarket, removeMarket } from './actions'

// ── All 30 markets with zip prefixes and search aliases ──────────────────────
const MARKETS = [
  { city: 'Nashville, TN',       zips: ['370','371','372','373','374','375','376','377','378','379'], aliases: ['nashville','music city'], desc: 'Legistar API · Permit tiers · Active enforcement' },
  { city: 'Austin, TX',          zips: ['737','786','787','788','789'], aliases: ['austin'], desc: 'July 1 deadline · 2,744 licenses · Council agenda scanning' },
  { city: 'Denver, CO',          zips: ['800','801','802','803','804','805'], aliases: ['denver','mile high'], desc: '7,449 licenses · SODA API · Legistar council monitoring' },
  { city: 'Scottsdale, AZ',      zips: ['852'], aliases: ['scottsdale'], desc: '2,999 licenses · ArcGIS API · TPT lodging tax' },
  { city: 'Palm Springs, CA',    zips: ['922'], aliases: ['palm springs','coachella valley'], desc: 'PrimeGov portal · Active enforcement · TOT' },
  { city: 'New Orleans, LA',     zips: ['700','701'], aliases: ['new orleans','nola'], desc: '1,300 licenses · Legistar + SODA API' },
  { city: 'San Diego, CA',       zips: ['919','920','921'], aliases: ['san diego','sd'], desc: '7,954 STRO licenses · 4-tier system' },
  { city: 'Charleston, SC',      zips: ['294'], aliases: ['charleston'], desc: 'Strict zoning overlay · ~700 permits' },
  { city: 'Savannah, GA',        zips: ['314'], aliases: ['savannah'], desc: 'STVR overlay · 20% ward cap · 8% hotel/motel tax' },
  { city: 'San Francisco, CA',   zips: ['941'], aliases: ['san francisco','sf','san fran'], desc: '$925 app fee · 90-night cap · Legistar monitoring' },
  { city: 'Miami Beach, FL',     zips: ['331'], aliases: ['miami','miami beach','south beach'], desc: '$20K+ fines · Strict zoning · 4 licenses required' },
  { city: 'Gatlinburg, TN',      zips: ['377'], aliases: ['gatlinburg','smoky mountains','smokies'], desc: 'Tourist Residency Permit · Smoky Mountains' },
  { city: 'Asheville, NC',       zips: ['287','288'], aliases: ['asheville'], desc: 'Whole-home STRs banned residential · Homestays only' },
  { city: 'Key West, FL',        zips: ['330','340'], aliases: ['key west','florida keys','keys'], desc: 'Finite transient licenses · 5% TDT · Monroe County' },
  { city: 'Sedona, AZ',          zips: ['863'], aliases: ['sedona'], desc: 'Annual permit · 1,200+ STRs · 24/7 hotline' },
  { city: 'Park City, UT',       zips: ['840'], aliases: ['park city'], desc: 'Nightly Rental License · Resort zones only' },
  { city: 'Breckenridge, CO',    zips: ['804'], aliases: ['breckenridge','breck','summit county'], desc: '4 STR zones with caps · Waitlists active' },
  { city: 'Big Bear, CA',        zips: ['923'], aliases: ['big bear','big bear lake'], desc: 'SB County permit · $1,144 app fee · Noise monitoring' },
  { city: 'Honolulu, HI',        zips: ['968'], aliases: ['honolulu','oahu','waikiki','hawaii'], desc: '90-day minimum residential · $500/day fines' },
  { city: 'Outer Banks, NC',     zips: ['279','272'], aliases: ['outer banks','obx','nags head','kill devil hills'], desc: 'Multi-jurisdiction · Largest US VR market' },
  { city: 'NYC, NY',             zips: ['100','101','102','103','104','110','111','112','113','114','116'], aliases: ['new york','new york city','nyc','manhattan','brooklyn','queens'], desc: 'OSE registration · Local Law 18 · Strict enforcement' },
  { city: 'Los Angeles, CA',     zips: ['900','901','902','903','904','905','906','907','908','910','911','912','913','914','915','916'], aliases: ['los angeles','la','hollywood','venice'], desc: 'Home Sharing Ordinance · $850 registration · HSO zones' },
  { city: 'Portland, OR',        zips: ['970','971','972'], aliases: ['portland','pdx'], desc: '11.5% TLT · $4/night fee · Quarterly filing' },
  { city: 'Orlando, FL',         zips: ['328','327','347','348'], aliases: ['orlando','disney','kissimmee'], desc: 'Home Sharing Registration · Orange County TDT' },
  { city: 'Las Vegas, NV',       zips: ['889','890','891'], aliases: ['las vegas','vegas'], desc: 'Clark County STR licensing · Business license required' },
  { city: 'Boston, MA',          zips: ['021','022'], aliases: ['boston'], desc: 'ISD registration · Legistar council monitoring' },
  { city: 'Maui, HI',            zips: ['967'], aliases: ['maui','lahaina','kihei','wailea'], desc: 'STRH permits · B&B permits · Planning commission' },
  { city: 'Lake Tahoe, CA',      zips: ['961','960','894','895'], aliases: ['lake tahoe','tahoe','south lake tahoe'], desc: 'El Dorado VHR · Placer County · Multi-jurisdiction' },
  { city: 'Tybee Island, GA',    zips: ['313'], aliases: ['tybee','tybee island'], desc: 'STVR certificate · Chatham County · GA hotel/motel fee' },
  { city: 'Destin, FL',          zips: ['325'], aliases: ['destin','30a','miramar beach','santa rosa beach'], desc: '6% TDT · Okaloosa County · FL DBPR license' },
]

function resolveMarkets(input: string): typeof MARKETS {
  const q = input.trim().toLowerCase()
  if (!q) return []

  // Check if input looks like a zip code (starts with digits)
  const zipMatch = q.replace(/\s/g, '').match(/^(\d{3,5})/)
  if (zipMatch) {
    const prefix = zipMatch[1].slice(0, 3)
    const matches = MARKETS.filter(m => m.zips.includes(prefix))
    if (matches.length > 0) return matches
  }

  // Text matching: check city name AND aliases
  return MARKETS.filter(m => {
    const searchable = [m.city.toLowerCase(), ...m.aliases].join(' ')
    const words = q.split(/[\s,]+/).filter(Boolean)
    return words.every(w => searchable.includes(w))
  })
}

// Popular markets shown as quick-pick chips
const POPULAR = ['Nashville, TN', 'Austin, TX', 'Denver, CO', 'Miami Beach, FL', 'San Diego, CA', 'San Francisco, CA', 'NYC, NY', 'Los Angeles, CA']

export default function MarketsClient({
  userId, savedCities, tier, maxMarkets, trialDaysLeft, isTrialActive, isPaid,
}: {
  userId: string; savedCities: string[]; tier: string; maxMarkets: number;
  trialDaysLeft: number; isTrialActive: boolean; isPaid: boolean;
}) {
  const [cities, setCities] = useState<string[]>(savedCities)
  const [isPending, startTransition] = useTransition()
  const [feedback, setFeedback] = useState<{ city: string; msg: string } | null>(null)
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState<typeof MARKETS>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const isFree = tier === 'free'
  const atLimit = cities.length >= maxMarkets

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node) &&
          inputRef.current && !inputRef.current.contains(e.target as Node)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  function handleInputChange(val: string) {
    setQuery(val)
    if (val.trim().length >= 2) {
      const results = resolveMarkets(val).filter(m => !cities.includes(m.city))
      setSuggestions(results)
      setShowSuggestions(true)
    } else {
      setSuggestions([])
      setShowSuggestions(false)
    }
  }

  async function handleUpgrade() {
    const res = await fetch('/api/stripe/checkout', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({tier: 'pro'}),
    })
    const data = await res.json()
    if (data.url) window.location.href = data.url
  }

  function showFeedback(city: string, msg: string) {
    setFeedback({ city, msg })
    setTimeout(() => setFeedback(null), 3000)
  }

  function handleAdd(city: string) {
    if (cities.includes(city)) return
    if (atLimit) { showFeedback(city, isFree ? 'Upgrade to Pro for unlimited markets' : 'Limit reached'); return }
    setCities(prev => [...prev, city])
    setQuery('')
    setSuggestions([])
    setShowSuggestions(false)
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

  const popularNotAdded = POPULAR.filter(c => !cities.includes(c))

  return (
    <div>
      <h1 style={{fontFamily:'var(--font-syne)',fontWeight:800,fontSize:'1.6rem',color:'var(--ink)',marginBottom:'0.4rem',letterSpacing:'-0.02em'}}>Your Markets</h1>
      <p style={{color:'var(--text-muted)',marginBottom:'1.5rem',fontSize:'0.9rem'}}>
        Enter a property address, zip code, or city name to add a market.
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

      {/* Free tier banner */}
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

      {/* ── Search input ── */}
      <div style={{position:'relative',marginBottom:'1.5rem'}}>
        <div style={{position:'relative'}}>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => handleInputChange(e.target.value)}
            onFocus={() => { if (suggestions.length > 0) setShowSuggestions(true) }}
            placeholder="Enter zip code, city, or address — e.g. 37201 or Nashville"
            style={{
              width:'100%',
              padding:'14px 18px 14px 42px',
              fontFamily:'var(--font-epilogue)',
              fontSize:'0.9rem',
              color:'var(--ink)',
              background:'white',
              border:'1.5px solid var(--border-mid)',
              borderRadius:'10px',
              outline:'none',
              transition:'border-color 0.2s',
            }}
            onMouseOver={e => (e.target as HTMLInputElement).style.borderColor = 'var(--green)'}
            onMouseOut={e => { if (document.activeElement !== e.target) (e.target as HTMLInputElement).style.borderColor = 'var(--border-mid)' }}
          />
          <svg style={{position:'absolute',left:'14px',top:'50%',transform:'translateY(-50%)',width:'18px',height:'18px',color:'var(--text-faint)'}} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>

        {/* Suggestions dropdown */}
        {showSuggestions && suggestions.length > 0 && (
          <div ref={dropdownRef} style={{
            position:'absolute',top:'100%',left:0,right:0,zIndex:50,
            marginTop:'4px',background:'white',border:'1.5px solid var(--border)',borderRadius:'10px',
            boxShadow:'0 8px 32px rgba(15,26,10,0.1)',overflow:'hidden',maxHeight:'320px',overflowY:'auto',
          }}>
            <div style={{padding:'8px 14px 6px',fontFamily:'var(--font-mono)',fontSize:'0.55rem',letterSpacing:'0.12em',textTransform:'uppercase',color:'var(--text-faint)'}}>
              {suggestions.length} market{suggestions.length !== 1 ? 's' : ''} found
            </div>
            {suggestions.map(m => (
              <button key={m.city} onClick={() => handleAdd(m.city)} style={{
                display:'flex',alignItems:'center',justifyContent:'space-between',
                width:'100%',padding:'12px 14px',border:'none',background:'none',
                cursor:atLimit ? 'default' : 'pointer',textAlign:'left',
                transition:'background 0.1s',
              }}
              onMouseOver={e => (e.currentTarget as HTMLButtonElement).style.background = 'var(--green-pale)'}
              onMouseOut={e => (e.currentTarget as HTMLButtonElement).style.background = 'none'}
              >
                <div>
                  <div style={{fontFamily:'var(--font-syne)',fontWeight:600,fontSize:'0.88rem',color:'var(--ink)'}}>{m.city}</div>
                  <div style={{fontFamily:'var(--font-mono)',fontSize:'0.56rem',color:'var(--text-faint)',letterSpacing:'0.04em',marginTop:'2px'}}>{m.desc}</div>
                </div>
                <span style={{fontFamily:'var(--font-syne)',fontWeight:700,fontSize:'0.7rem',color:atLimit ? '#b87d2d' : 'var(--green)',whiteSpace:'nowrap',flexShrink:0,marginLeft:'12px'}}>
                  {atLimit && isFree ? 'Upgrade' : '+ Add'}
                </span>
              </button>
            ))}
          </div>
        )}

        {/* No results message */}
        {showSuggestions && query.trim().length >= 2 && suggestions.length === 0 && (
          <div style={{
            position:'absolute',top:'100%',left:0,right:0,zIndex:50,
            marginTop:'4px',background:'white',border:'1.5px solid var(--border)',borderRadius:'10px',
            boxShadow:'0 8px 32px rgba(15,26,10,0.1)',padding:'16px',textAlign:'center',
          }}>
            <div style={{fontFamily:'var(--font-mono)',fontSize:'0.62rem',color:'var(--text-faint)',letterSpacing:'0.06em'}}>
              No monitored markets match "{query}" — we're adding new cities regularly
            </div>
          </div>
        )}
      </div>

      {/* ── Quick-pick chips (popular markets not yet added) ── */}
      {popularNotAdded.length > 0 && cities.length < 3 && (
        <div style={{marginBottom:'1.5rem'}}>
          <div style={{fontFamily:'var(--font-mono)',fontSize:'0.55rem',letterSpacing:'0.15em',textTransform:'uppercase',color:'var(--text-faint)',marginBottom:'8px'}}>
            Popular markets
          </div>
          <div style={{display:'flex',flexWrap:'wrap',gap:'6px'}}>
            {popularNotAdded.slice(0, 6).map(city => (
              <button key={city} onClick={() => handleAdd(city)} style={{
                fontFamily:'var(--font-mono)',fontSize:'0.62rem',letterSpacing:'0.04em',
                padding:'6px 12px',borderRadius:'100px',border:'1.5px solid var(--border)',
                background:'white',color:'var(--text-mid)',cursor:atLimit ? 'default' : 'pointer',
                transition:'all 0.15s',
              }}
              onMouseOver={e => { (e.target as HTMLButtonElement).style.borderColor = 'var(--green-light)'; (e.target as HTMLButtonElement).style.background = 'var(--green-pale)' }}
              onMouseOut={e => { (e.target as HTMLButtonElement).style.borderColor = 'var(--border)'; (e.target as HTMLButtonElement).style.background = 'white' }}
              >
                + {city.split(',')[0]}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Tracked markets list ── */}
      {cities.length > 0 && (
        <div style={{marginBottom:'1rem'}}>
          <div style={{fontFamily:'var(--font-mono)',fontSize:'0.6rem',letterSpacing:'0.15em',textTransform:'uppercase',color:'var(--text-faint)',marginBottom:'0.75rem'}}>
            Tracking {cities.length} market{cities.length !== 1 ? 's' : ''}
          </div>
          <div style={{display:'flex',flexDirection:'column',gap:'8px'}}>
            {cities.map(city => {
              const market = MARKETS.find(m => m.city === city)
              return (
                <div key={city} style={{display:'flex',alignItems:'center',justifyContent:'space-between',background:'var(--green-pale)',border:'1.5px solid var(--green-light)',borderRadius:'10px',padding:'14px 18px'}}>
                  <div style={{display:'flex',alignItems:'center',gap:'10px',flex:1,minWidth:0}}>
                    <div style={{width:'8px',height:'8px',background:'var(--green-bright)',borderRadius:'50%',flexShrink:0}} />
                    <div style={{minWidth:0}}>
                      <span style={{fontFamily:'var(--font-syne)',fontWeight:600,fontSize:'0.9rem',color:'var(--ink)'}}>{city}</span>
                      {market && <div style={{fontFamily:'var(--font-mono)',fontSize:'0.55rem',color:'var(--text-faint)',letterSpacing:'0.04em',marginTop:'2px',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{market.desc}</div>}
                    </div>
                    {feedback?.city === city && <span style={{fontFamily:'var(--font-mono)',fontSize:'0.6rem',color:feedback.msg.includes('Upgrade') ? '#b87d2d' : 'var(--green)',letterSpacing:'0.05em',flexShrink:0,marginLeft:'8px'}}>{feedback.msg}</span>}
                  </div>
                  <button onClick={() => handleRemove(city)} disabled={isPending}
                    style={{fontFamily:'var(--font-mono)',fontSize:'0.58rem',letterSpacing:'0.1em',textTransform:'uppercase',color:'var(--text-faint)',background:'none',border:'none',cursor:isFree ? 'not-allowed' : 'pointer',padding:'4px 8px',opacity:isFree ? 0.5 : 1,flexShrink:0}}
                    title={isFree ? 'Upgrade to change markets' : 'Remove market'}>
                    {isFree ? 'Locked' : 'Remove'}
                  </button>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {cities.length === 0 && (
        <div style={{marginTop:'1rem',padding:'24px',background:'var(--off-white)',border:'1px solid var(--border)',borderRadius:'10px',textAlign:'center'}}>
          <p style={{fontFamily:'var(--font-syne)',fontWeight:600,fontSize:'0.95rem',color:'var(--text-mid)',marginBottom:'4px'}}>No markets yet</p>
          <p style={{fontFamily:'var(--font-mono)',fontSize:'0.62rem',letterSpacing:'0.06em',color:'var(--text-faint)'}}>Type a zip code or city name above to add your first market</p>
        </div>
      )}

      {/* ── 30 markets badge ── */}
      <div style={{marginTop:'2rem',padding:'14px 18px',background:'white',border:'1px solid var(--border)',borderRadius:'10px',display:'flex',alignItems:'center',gap:'10px'}}>
        <div style={{width:'8px',height:'8px',background:'var(--green-bright)',borderRadius:'50%',animation:'pulse 2s ease-in-out infinite'}} />
        <span style={{fontFamily:'var(--font-mono)',fontSize:'0.6rem',letterSpacing:'0.08em',color:'var(--text-muted)'}}>
          Monitoring <strong style={{color:'var(--green)'}}>30 US markets</strong> with active scraping · Nashville, Austin, Denver, NYC, LA, SF, and 24 more
        </span>
      </div>
    </div>
  )
}
