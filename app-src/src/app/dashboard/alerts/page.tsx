import { auth } from '@clerk/nextjs/server'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'

const URGENCY_COLORS: Record<string, {bg:string;border:string;text:string}> = {
  high:   {bg:'#fff0ee',border:'#f7c8c8',text:'#b84040'},
  medium: {bg:'#fdf3e3',border:'#f5d9a0',text:'#b87d2d'},
  low:    {bg:'#e8f5ee',border:'#c8ecd8',text:'#2d7a4f'},
}

export default async function AlertsPage() {
  const { userId } = await auth()
  if (!userId) redirect('/sign-in')
  const supabase = createClient()

  // Get user's saved markets first
  const { data: userMarkets } = await supabase
    .from('user_markets')
    .select('city')
    .eq('user_id', userId)

  const cities = (userMarkets || []).map((m: { city: string }) => m.city)

  // Fetch alerts for any of the user's cities
  const { data: alerts } = cities.length > 0
    ? await supabase
        .from('alerts')
        .select('*')
        .in('city', cities)
        .order('sent_at', { ascending: false })
        .limit(50)
    : { data: [] }

  return (
    <div>
      <h1 style={{fontFamily:'var(--font-syne)',fontWeight:800,fontSize:'1.6rem',color:'var(--ink)',marginBottom:'4px',letterSpacing:'-0.02em'}}>Alert History</h1>
      <p style={{fontSize:'0.875rem',color:'var(--text-muted)',marginBottom:'32px'}}>All regulation alerts sent to your markets.</p>
      <div style={{background:'white',border:'1.5px solid var(--border)',borderRadius:'12px',overflow:'hidden'}}>
        {(!alerts||alerts.length===0) ? (
          <div style={{padding:'48px 20px',textAlign:'center'}}>
            <p style={{fontFamily:'var(--font-mono)',fontSize:'0.65rem',letterSpacing:'0.08em',color:'var(--text-faint)'}}>No alerts yet. You'll be notified when regulations change in your markets.</p>
          </div>
        ) : alerts.map((alert:any, i:number) => {
          const c = URGENCY_COLORS[alert.urgency]||URGENCY_COLORS.medium
          const date = new Date(alert.sent_at).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',hour:'2-digit',minute:'2-digit'})
          const hasChecklist = alert.checklist && alert.checklist.trim().length > 0
          return (
            <div key={alert.id} style={{padding:'20px',borderBottom:i<alerts.length-1?'1px solid var(--border)':'none'}}>
              <div style={{display:'flex',alignItems:'flex-start',gap:'12px'}}>
                <span style={{display:'inline-block',background:c.bg,border:`1px solid ${c.border}`,color:c.text,fontSize:'0.58rem',letterSpacing:'0.1em',textTransform:'uppercase',padding:'3px 8px',borderRadius:'100px',whiteSpace:'nowrap',marginTop:'2px'}}>{alert.urgency}</span>
                <div style={{flex:1}}>
                  <div style={{fontFamily:'var(--font-syne)',fontWeight:700,fontSize:'0.95rem',color:'var(--ink)',marginBottom:'4px'}}>{alert.headline}</div>
                  <div style={{fontFamily:'var(--font-mono)',fontSize:'0.58rem',color:'var(--text-faint)',letterSpacing:'0.05em',marginBottom:'8px'}}>{alert.city} · {date}</div>
                  {alert.detail && <div style={{fontSize:'0.82rem',color:'var(--text-mid)',lineHeight:1.6,background:'var(--off-white)',border:'1px solid var(--border)',borderRadius:'6px',padding:'10px 12px',marginBottom:'8px'}}>{alert.detail}</div>}
                  {hasChecklist && (
                    <div
                      style={{marginBottom:'8px'}}
                      dangerouslySetInnerHTML={{__html: alert.checklist}}
                    />
                  )}
                  {alert.source_url && <a href={alert.source_url} target="_blank" rel="noopener noreferrer" style={{fontFamily:'var(--font-mono)',fontSize:'0.6rem',color:'var(--green)',letterSpacing:'0.05em'}}>View source →</a>}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
