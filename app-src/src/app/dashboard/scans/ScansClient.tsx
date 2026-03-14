'use client'

import { useState } from 'react'

const RISK_COLORS: Record<string, {bg:string;border:string;text:string;label:string}> = {
  low:    {bg:'#e8f5ee',border:'#c8ecd8',text:'#2d7a4f',label:'Low risk'},
  medium: {bg:'#fdf3e3',border:'#f5d9a0',text:'#b87d2d',label:'Medium risk'},
  high:   {bg:'#fff0ee',border:'#f7c8c8',text:'#b84040',label:'High risk'},
}

const BETA_CITIES = ['Nashville, TN', 'Austin, TX', 'Denver, CO', 'Scottsdale, AZ', 'Palm Springs, CA']

export default function ScansClient({
  userId, scans: initialScans, canScan, tier,
}: {
  userId: string; scans: any[]; canScan: boolean; tier: string;
}) {
  const [scans, setScans] = useState(initialScans)
  const [city, setCity] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [activeReport, setActiveReport] = useState<any>(null)
  const [activeCity, setActiveCity] = useState('')
  const [activeEnriched, setActiveEnriched] = useState(false)

  async function handleGenerate() {
    if (!city.trim()) { setError('Enter a city name'); return }
    setLoading(true)
    setError('')
    setActiveReport(null)

    try {
      const res = await fetch('/api/scans/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ city: city.trim() }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.error || 'Failed to generate report')
        setLoading(false)
        return
      }
      setActiveReport(data.report)
      setActiveCity(city.trim())
      setActiveEnriched(data.is_enriched)
      // Prepend to history
      setScans(prev => [{
        id: data.id,
        city: city.trim(),
        is_enriched: data.is_enriched,
        created_at: new Date().toISOString(),
        report: data.report,
      }, ...prev])
      setCity('')
    } catch (e) {
      setError('Network error — try again')
    }
    setLoading(false)
  }

  function viewReport(scan: any) {
    setActiveReport(scan.report)
    setActiveCity(scan.city)
    setActiveEnriched(scan.is_enriched)
  }

  return (
    <div>
      <h1 style={{fontFamily:'var(--font-syne)',fontWeight:800,fontSize:'1.6rem',color:'var(--ink)',marginBottom:'4px',letterSpacing:'-0.02em'}}>Market Scans</h1>
      <p style={{fontSize:'0.875rem',color:'var(--text-muted)',marginBottom:'32px'}}>Generate a pre-investment regulation report for any US city.</p>

      {/* Upgrade banner for free users */}
      {!canScan && (
        <div style={{marginBottom:'24px',padding:'12px 16px',background:'#fdf3e3',border:'1.5px solid #f5d9a0',borderRadius:'8px'}}>
          <span style={{fontFamily:'var(--font-mono)',fontSize:'0.62rem',letterSpacing:'0.08em',color:'#b87d2d'}}>
            FREE PLAN · Market scans require Pro. <a href="/dashboard/markets" style={{color:'#1a4d2e',fontWeight:700}}>Upgrade →</a>
          </span>
        </div>
      )}

      {/* Generate form */}
      {canScan && (
        <div style={{background:'white',border:'1.5px solid var(--border)',borderRadius:'12px',padding:'20px 24px',marginBottom:'24px'}}>
          <div style={{fontFamily:'var(--font-mono)',fontSize:'0.6rem',letterSpacing:'0.15em',textTransform:'uppercase',color:'var(--green)',marginBottom:'12px'}}>New scan</div>
          <div style={{display:'flex',gap:'10px',alignItems:'flex-start'}}>
            <div style={{flex:1,position:'relative'}}>
              <input
                type="text"
                value={city}
                onChange={e => { setCity(e.target.value); setError('') }}
                onKeyDown={e => e.key === 'Enter' && !loading && handleGenerate()}
                placeholder="Enter any US city (e.g. Charleston, SC)"
                disabled={loading}
                style={{width:'100%',padding:'12px 16px',border:'1.5px solid var(--border-mid)',borderRadius:'8px',fontSize:'0.9rem',fontFamily:'var(--font-sans)',outline:'none'}}
              />
              {/* Quick select beta cities */}
              <div style={{display:'flex',gap:'6px',marginTop:'8px',flexWrap:'wrap'}}>
                {BETA_CITIES.map(c => (
                  <button key={c} onClick={() => setCity(c)}
                    style={{fontFamily:'var(--font-mono)',fontSize:'0.55rem',letterSpacing:'0.06em',padding:'4px 10px',borderRadius:'100px',background:'var(--green-pale)',border:'1px solid var(--green-light)',color:'var(--green)',cursor:'pointer'}}
                  >{c.split(',')[0]}</button>
                ))}
                <span style={{fontFamily:'var(--font-mono)',fontSize:'0.52rem',color:'var(--text-faint)',alignSelf:'center',marginLeft:'4px'}}>← enriched with live data</span>
              </div>
            </div>
            <button
              onClick={handleGenerate}
              disabled={loading || !city.trim()}
              style={{fontFamily:'var(--font-syne)',fontWeight:700,fontSize:'0.75rem',padding:'12px 24px',background:loading ? 'var(--border)' : 'var(--green-deep)',color:'white',borderRadius:'8px',border:'none',cursor:loading ? 'wait' : 'pointer',whiteSpace:'nowrap'}}
            >
              {loading ? 'Generating...' : 'Run scan'}
            </button>
          </div>
          {error && <div style={{fontFamily:'var(--font-mono)',fontSize:'0.62rem',color:'#b84040',marginTop:'8px'}}>{error}</div>}
          {loading && (
            <div style={{marginTop:'12px',padding:'12px 16px',background:'var(--green-pale)',border:'1px solid var(--green-light)',borderRadius:'8px'}}>
              <span style={{fontFamily:'var(--font-mono)',fontSize:'0.62rem',color:'var(--green)',letterSpacing:'0.05em'}}>
                Analyzing regulations for {city}... This takes 10-15 seconds.
              </span>
            </div>
          )}
        </div>
      )}

      {/* Active report display */}
      {activeReport && <ReportView report={activeReport} city={activeCity} isEnriched={activeEnriched} onClose={() => setActiveReport(null)} />}

      {/* Scan history */}
      {scans.length > 0 && !activeReport && (
        <div>
          <div style={{fontFamily:'var(--font-mono)',fontSize:'0.6rem',letterSpacing:'0.15em',textTransform:'uppercase',color:'var(--text-faint)',marginBottom:'12px'}}>
            Scan history
          </div>
          <div style={{display:'flex',flexDirection:'column',gap:'10px'}}>
            {scans.map((scan: any) => {
              const risk = RISK_COLORS[scan.report?.risk_level] || RISK_COLORS.medium
              const date = new Date(scan.created_at).toLocaleDateString('en-US', {month:'short',day:'numeric',year:'numeric'})
              return (
                <div key={scan.id} style={{background:'white',border:'1.5px solid var(--border)',borderRadius:'10px',padding:'16px 20px',display:'flex',alignItems:'center',justifyContent:'space-between',cursor:'pointer'}} onClick={() => viewReport(scan)}>
                  <div style={{display:'flex',alignItems:'center',gap:'12px'}}>
                    <span style={{fontFamily:'var(--font-mono)',fontSize:'0.56rem',letterSpacing:'0.08em',textTransform:'uppercase',padding:'3px 8px',borderRadius:'100px',background:risk.bg,border:`1px solid ${risk.border}`,color:risk.text}}>{risk.label}</span>
                    <div>
                      <div style={{fontFamily:'var(--font-syne)',fontWeight:600,fontSize:'0.9rem',color:'var(--ink)'}}>{scan.city}</div>
                      <div style={{fontFamily:'var(--font-mono)',fontSize:'0.55rem',color:'var(--text-faint)',letterSpacing:'0.05em'}}>
                        {date} {scan.is_enriched && '· Enriched with live data'}
                      </div>
                    </div>
                  </div>
                  <span style={{fontFamily:'var(--font-mono)',fontSize:'0.6rem',color:'var(--green)',letterSpacing:'0.05em'}}>View →</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Empty state */}
      {scans.length === 0 && !activeReport && canScan && (
        <div style={{background:'white',border:'1.5px solid var(--border)',borderRadius:'12px',padding:'48px 20px',textAlign:'center'}}>
          <p style={{fontFamily:'var(--font-mono)',fontSize:'0.65rem',letterSpacing:'0.08em',color:'var(--text-faint)'}}>
            No scans yet. Enter a city above to generate your first market regulation report.
          </p>
        </div>
      )}
    </div>
  )
}


function ReportView({ report, city, isEnriched, onClose }: {
  report: any; city: string; isEnriched: boolean; onClose: () => void;
}) {
  const risk = RISK_COLORS[report.risk_level] || RISK_COLORS.medium
  const sections = report.sections || {}

  return (
    <div style={{marginBottom:'32px'}}>
      <button onClick={onClose} style={{fontFamily:'var(--font-mono)',fontSize:'0.6rem',letterSpacing:'0.08em',color:'var(--green)',background:'none',border:'none',cursor:'pointer',marginBottom:'16px',padding:0}}>
        ← Back to scan history
      </button>

      <div style={{background:'white',border:'1.5px solid var(--border)',borderRadius:'12px',overflow:'hidden'}}>
        {/* Report header */}
        <div style={{background:'var(--green-deep)',padding:'24px 28px'}}>
          <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:'8px'}}>
            <span style={{fontFamily:'var(--font-mono)',fontSize:'0.6rem',letterSpacing:'0.15em',textTransform:'uppercase',color:'rgba(255,255,255,0.5)'}}>STRWatch Market Scan</span>
            <div style={{display:'flex',gap:'8px',alignItems:'center'}}>
              {isEnriched && (
                <span style={{fontFamily:'var(--font-mono)',fontSize:'0.52rem',letterSpacing:'0.08em',textTransform:'uppercase',padding:'3px 10px',borderRadius:'100px',background:'rgba(168,230,195,0.15)',border:'1px solid rgba(168,230,195,0.25)',color:'#a8e6c3'}}>Live data</span>
              )}
              <span style={{fontFamily:'var(--font-mono)',fontSize:'0.52rem',letterSpacing:'0.08em',textTransform:'uppercase',padding:'3px 10px',borderRadius:'100px',background:risk.bg,border:`1px solid ${risk.border}`,color:risk.text}}>{risk.label}</span>
            </div>
          </div>
          <div style={{fontFamily:'var(--font-syne)',fontWeight:800,fontSize:'1.5rem',color:'white',letterSpacing:'-0.02em'}}>{city}</div>
          <div style={{fontFamily:'var(--font-mono)',fontSize:'0.58rem',color:'rgba(255,255,255,0.4)',marginTop:'4px'}}>{report.generated_at}</div>
        </div>

        {/* Summary */}
        <div style={{padding:'20px 28px',borderBottom:'1px solid var(--border)'}}>
          <div style={{fontSize:'0.9rem',color:'var(--text-mid)',lineHeight:1.7}}>{report.summary}</div>
        </div>

        {/* Sections */}
        {Object.values(sections).map((section: any, idx: number) => (
          <div key={idx} style={{padding:'20px 28px',borderBottom:'1px solid var(--border)'}}>
            <div style={{fontFamily:'var(--font-syne)',fontWeight:700,fontSize:'0.95rem',color:'var(--ink)',marginBottom:'14px'}}>{section.title}</div>
            <div style={{display:'flex',flexDirection:'column',gap:'10px'}}>
              {(section.items || []).map((item: any, i: number) => (
                <div key={i} style={{display:'flex',gap:'12px',alignItems:'flex-start'}}>
                  <div style={{minWidth:'140px',flexShrink:0}}>
                    <div style={{fontFamily:'var(--font-syne)',fontWeight:600,fontSize:'0.82rem',color:'var(--ink)'}}>{item.label}</div>
                  </div>
                  <div style={{flex:1}}>
                    <div style={{fontFamily:'var(--font-syne)',fontWeight:700,fontSize:'0.82rem',color:'var(--green-deep)',marginBottom:'2px'}}>{item.value}</div>
                    {item.detail && <div style={{fontSize:'0.78rem',color:'var(--text-muted)',lineHeight:1.55}}>{item.detail}</div>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* Key contacts */}
        {report.key_contacts && report.key_contacts.length > 0 && (
          <div style={{padding:'20px 28px',borderBottom:'1px solid var(--border)'}}>
            <div style={{fontFamily:'var(--font-syne)',fontWeight:700,fontSize:'0.95rem',color:'var(--ink)',marginBottom:'14px'}}>Key Contacts</div>
            <div style={{display:'flex',flexDirection:'column',gap:'8px'}}>
              {report.key_contacts.map((contact: any, i: number) => (
                <div key={i} style={{display:'flex',gap:'12px',alignItems:'center'}}>
                  <span style={{fontFamily:'var(--font-syne)',fontWeight:600,fontSize:'0.82rem',color:'var(--ink)',minWidth:'200px'}}>{contact.name}</span>
                  {contact.phone && <span style={{fontFamily:'var(--font-mono)',fontSize:'0.72rem',color:'var(--text-muted)'}}>{contact.phone}</span>}
                  {contact.url && <a href={contact.url} target="_blank" rel="noopener noreferrer" style={{fontFamily:'var(--font-mono)',fontSize:'0.6rem',color:'var(--green)'}}>Website →</a>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Disclaimer */}
        <div style={{padding:'16px 28px',background:'var(--off-white)'}}>
          <p style={{fontFamily:'var(--font-mono)',fontSize:'0.58rem',color:'var(--text-faint)',lineHeight:1.6,letterSpacing:'0.03em'}}>
            {report.disclaimer || 'This report is for informational purposes only and does not constitute legal advice. Verify all details with local government before making investment decisions.'}
          </p>
        </div>
      </div>
    </div>
  )
}
