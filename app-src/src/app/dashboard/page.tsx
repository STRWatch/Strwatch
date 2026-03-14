import { auth } from '@clerk/nextjs/server'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import Link from 'next/link'

const AUSTIN_DEADLINE = new Date('2026-07-01')
function daysToDeadline() {
  return Math.max(0, Math.ceil((AUSTIN_DEADLINE.getTime() - Date.now()) / 86400000))
}
const URGENCY_COLORS: Record<string, {bg:string;border:string;text:string}> = {
  high:   {bg:'#fff0ee',border:'#f7c8c8',text:'#b84040'},
  medium: {bg:'#fdf3e3',border:'#f5d9a0',text:'#b87d2d'},
  low:    {bg:'#e8f5ee',border:'#c8ecd8',text:'#2d7a4f'},
}

export default async function DashboardPage() {
  const { userId } = await auth()
  if (!userId) redirect('/sign-in')
  const supabase = createClient()
  const { data: markets } = await supabase.from('user_markets').select('city').eq('user_id', userId)
  const { data: alerts } = await supabase.from('alerts').select('*').eq('user_id', userId).order('sent_at', {ascending:false}).limit(10)
  const thisMonth = new Date(); thisMonth.setDate(1); thisMonth.setHours(0,0,0,0)
  const alertsThisMonth = (alerts||[]).filter(a => new Date(a.sent_at) >= thisMonth).length
  const marketCount = (markets||[]).length
  const days = daysToDeadline()

  return (
    <div>
      <h1 style={{fontFamily:'var(--font-syne)',fontWeight:800,fontSize:'1.6rem',color:'var(--ink)',marginBottom:'4px',letterSpacing:'-0.02em'}}>Compliance Overview</h1>
      <p style={{fontSize:'0.875rem',color:'var(--text-muted)',marginBottom:'32px'}}>Your markets, recent alerts, and upcoming deadlines.</p>
      <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:'16px',marginBottom:'32px'}}>
        <div style={{background:'white',border:'1.5px solid var(--border)',borderRadius:'12px',padding:'20px'}}>
          <div style={{fontSize:'2rem',fontWeight:800,color:'var(--ink)',lineHeight:1,marginBottom:'8px'}}>{marketCount > 0 ? marketCount : '—'}</div>
          <div style={{fontSize:'0.7rem',color:'var(--text-faint)',textTransform:'uppercase',letterSpacing:'0.1em'}}>
            {marketCount === 0 ? <><span>Markets tracked · </span><Link href="/dashboard/markets" style={{color:'var(--green)'}}>Add one →</Link></> : 'Markets tracked'}
          </div>
        </div>
        <div style={{background:'white',border:'1.5px solid var(--border)',borderRadius:'12px',padding:'20px'}}>
          <div style={{fontSize:'2rem',fontWeight:800,color:'var(--ink)',lineHeight:1,marginBottom:'8px'}}>{alertsThisMonth}</div>
          <div style={{fontSize:'0.7rem',color:'var(--text-faint)',textTransform:'uppercase',letterSpacing:'0.1em'}}>Alerts this month</div>
        </div>
        <div style={{background:'var(--green-pale)',border:'1.5px solid var(--green-light)',borderRadius:'12px',padding:'20px'}}>
          <div style={{fontSize:'2rem',fontWeight:800,color:'var(--green-deep)',lineHeight:1,marginBottom:'8px'}}>{days}</div>
          <div style={{fontSize:'0.7rem',color:'var(--green)',textTransform:'uppercase',letterSpacing:'0.1em'}}>Days to Austin deadline</div>
        </div>
      </div>
      <div style={{background:'white',border:'1.5px solid var(--border)',borderRadius:'12px',overflow:'hidden'}}>
        <div style={{padding:'16px 20px',borderBottom:'1px solid var(--border)',display:'flex',justifyContent:'space-between',alignItems:'center'}}>
          <span style={{fontFamily:'var(--font-syne)',fontWeight:700,fontSize:'0.95rem',color:'var(--ink)'}}>Recent Alerts</span>
          {(alerts||[]).length > 0 && <Link href="/dashboard/alerts" style={{fontFamily:'var(--font-mono)',fontSize:'0.6rem',letterSpacing:'0.1em',textTransform:'uppercase',color:'var(--green)'}}>View all →</Link>}
        </div>
        {(alerts||[]).length === 0 ? (
          <div style={{padding:'32px 20px',textAlign:'center'}}>
            <p style={{fontFamily:'var(--font-mono)',fontSize:'0.65rem',letterSpacing:'0.08em',color:'var(--text-faint)'}}>
              {marketCount === 0 ? <><span>No alerts yet. </span><Link href="/dashboard/markets" style={{color:'var(--green)'}}>Add your markets →</Link></> : "No alerts yet. You'll be notified when regulations change in your markets."}
            </p>
          </div>
        ) : (alerts||[]).slice(0,5).map((alert:any) => {
          const c = URGENCY_COLORS[alert.urgency]||URGENCY_COLORS.medium
          const date = new Date(alert.sent_at).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'})
          return (
            <div key={alert.id} style={{padding:'16px 20px',borderBottom:'1px solid var(--border)',display:'flex',gap:'12px',alignItems:'flex-start'}}>
              <span style={{display:'inline-block',background:c.bg,border:`1px solid ${c.border}`,color:c.text,fontSize:'0.58rem',letterSpacing:'0.1em',textTransform:'uppercase',padding:'3px 8px',borderRadius:'100px',whiteSpace:'nowrap',marginTop:'2px'}}>{alert.urgency}</span>
              <div style={{flex:1}}>
                <div style={{fontFamily:'var(--font-syne)',fontWeight:600,fontSize:'0.88rem',color:'var(--ink)',marginBottom:'2px'}}>{alert.headline}</div>
                <div style={{fontFamily:'var(--font-mono)',fontSize:'0.58rem',color:'var(--text-faint)',letterSpacing:'0.05em'}}>{alert.city} · {date}</div>
              </div>
              {alert.source_url && <a href={alert.source_url} target="_blank" rel="noopener noreferrer" style={{fontFamily:'var(--font-mono)',fontSize:'0.58rem',color:'var(--green)',letterSpacing:'0.05em',whiteSpace:'nowrap'}}>Source →</a>}
            </div>
          )
        })}
      </div>
    </div>
  )
}
