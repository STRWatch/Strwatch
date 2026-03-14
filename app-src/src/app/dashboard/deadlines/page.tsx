import { auth } from '@clerk/nextjs/server'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'

const CATEGORY_LABELS: Record<string, {label:string;bg:string;border:string;text:string}> = {
  permit:       {label:'Permit',bg:'#eef3ff',border:'#c8d8f7',text:'#3a5cb8'},
  enforcement:  {label:'Enforcement',bg:'#fff0ee',border:'#f7c8c8',text:'#b84040'},
  legislation:  {label:'Legislation',bg:'#fdf3e3',border:'#f5d9a0',text:'#b87d2d'},
}

function getUrgency(dateStr: string): {label:string;bg:string;border:string;text:string;sort:number} {
  const now = new Date()
  const deadline = new Date(dateStr + 'T00:00:00')
  const days = Math.ceil((deadline.getTime() - now.getTime()) / 86400000)
  if (days < 0) return {label:`${Math.abs(days)}d overdue`,bg:'#fff0ee',border:'#f7c8c8',text:'#b84040',sort:-1}
  if (days <= 30) return {label:`${days}d left`,bg:'#fff0ee',border:'#f7c8c8',text:'#b84040',sort:0}
  if (days <= 90) return {label:`${days}d left`,bg:'#fdf3e3',border:'#f5d9a0',text:'#b87d2d',sort:1}
  return {label:`${days}d left`,bg:'#e8f5ee',border:'#c8ecd8',text:'#2d7a4f',sort:2}
}

export default async function DeadlinesPage() {
  const { userId } = await auth()
  if (!userId) redirect('/sign-in')
  const supabase = createClient()

  const { data: markets } = await supabase
    .from('user_markets')
    .select('city')
    .eq('user_id', userId)

  const userCities = (markets || []).map((m: {city:string}) => m.city)

  let deadlines: any[] = []
  if (userCities.length > 0) {
    const { data } = await supabase
      .from('deadlines')
      .select('*')
      .in('city', userCities)
      .order('deadline_date', { ascending: true })
    deadlines = data || []
  }

  return (
    <div>
      <h1 style={{fontFamily:'var(--font-syne)',fontWeight:800,fontSize:'1.6rem',color:'var(--ink)',marginBottom:'4px',letterSpacing:'-0.02em'}}>Permit Deadlines</h1>
      <p style={{fontSize:'0.875rem',color:'var(--text-muted)',marginBottom:'32px'}}>Upcoming deadlines and renewal dates for your markets. Never miss a permit window.</p>

      {userCities.length === 0 ? (
        <div style={{background:'white',border:'1.5px solid var(--border)',borderRadius:'12px',padding:'48px 20px',textAlign:'center'}}>
          <p style={{fontFamily:'var(--font-mono)',fontSize:'0.65rem',letterSpacing:'0.08em',color:'var(--text-faint)'}}>
            No markets added yet. <a href="/dashboard/markets" style={{color:'var(--green)'}}>Add your markets →</a> to see upcoming deadlines.
          </p>
        </div>
      ) : deadlines.length === 0 ? (
        <div style={{background:'white',border:'1.5px solid var(--border)',borderRadius:'12px',padding:'48px 20px',textAlign:'center'}}>
          <p style={{fontFamily:'var(--font-mono)',fontSize:'0.65rem',letterSpacing:'0.08em',color:'var(--text-faint)'}}>
            No deadlines found for your markets. We'll add them as we detect them.
          </p>
        </div>
      ) : (
        <div style={{display:'flex',flexDirection:'column',gap:'12px'}}>
          {deadlines.map((d: any) => {
            const urgency = getUrgency(d.deadline_date)
            const cat = CATEGORY_LABELS[d.category] || CATEGORY_LABELS.permit
            const dateFormatted = new Date(d.deadline_date + 'T00:00:00').toLocaleDateString('en-US', {month:'long',day:'numeric',year:'numeric'})
            return (
              <div key={d.id} style={{background:'white',border:'1.5px solid var(--border)',borderRadius:'12px',padding:'20px 24px',display:'flex',gap:'16px',alignItems:'flex-start'}}>
                {/* Date column */}
                <div style={{minWidth:'80px',textAlign:'center',flexShrink:0}}>
                  <div style={{fontFamily:'var(--font-syne)',fontWeight:800,fontSize:'1.5rem',color:'var(--ink)',lineHeight:1}}>
                    {new Date(d.deadline_date + 'T00:00:00').toLocaleDateString('en-US',{month:'short'}).toUpperCase()}
                  </div>
                  <div style={{fontFamily:'var(--font-syne)',fontWeight:800,fontSize:'2rem',color:'var(--ink)',lineHeight:1,marginTop:'2px'}}>
                    {new Date(d.deadline_date + 'T00:00:00').getDate()}
                  </div>
                  <div style={{fontFamily:'var(--font-mono)',fontSize:'0.55rem',color:'var(--text-faint)',marginTop:'4px'}}>
                    {new Date(d.deadline_date + 'T00:00:00').getFullYear()}
                  </div>
                </div>

                {/* Content */}
                <div style={{flex:1}}>
                  <div style={{display:'flex',alignItems:'center',gap:'8px',marginBottom:'6px',flexWrap:'wrap'}}>
                    <span style={{fontFamily:'var(--font-mono)',fontSize:'0.56rem',letterSpacing:'0.08em',textTransform:'uppercase',padding:'3px 8px',borderRadius:'100px',background:urgency.bg,border:`1px solid ${urgency.border}`,color:urgency.text,whiteSpace:'nowrap'}}>{urgency.label}</span>
                    <span style={{fontFamily:'var(--font-mono)',fontSize:'0.56rem',letterSpacing:'0.08em',textTransform:'uppercase',padding:'3px 8px',borderRadius:'100px',background:cat.bg,border:`1px solid ${cat.border}`,color:cat.text,whiteSpace:'nowrap'}}>{cat.label}</span>
                    <span style={{fontFamily:'var(--font-mono)',fontSize:'0.56rem',color:'var(--text-faint)',letterSpacing:'0.05em'}}>{d.city}</span>
                  </div>
                  <div style={{fontFamily:'var(--font-syne)',fontWeight:700,fontSize:'0.95rem',color:'var(--ink)',marginBottom:'4px',lineHeight:1.35}}>{d.title}</div>
                  {d.description && (
                    <div style={{fontSize:'0.82rem',color:'var(--text-mid)',lineHeight:1.6,marginBottom:'6px'}}>{d.description}</div>
                  )}
                  {d.source_url && (
                    <a href={d.source_url} target="_blank" rel="noopener noreferrer" style={{fontFamily:'var(--font-mono)',fontSize:'0.58rem',color:'var(--green)',letterSpacing:'0.05em'}}>View source →</a>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
