import { auth } from '@clerk/nextjs/server'
import { redirect } from 'next/navigation'

export default async function DashboardPage() {
  const { userId } = await auth()
  if (!userId) redirect('/sign-in')

  return (
    <div>
      <h1 style={{fontSize:'1.5rem', fontWeight:800, color:'#0f1a0a', marginBottom:'4px'}}>Compliance Overview</h1>
      <p style={{fontSize:'0.875rem', color:'#6b7280', marginBottom:'32px'}}>Your markets, recent alerts, and upcoming deadlines.</p>

      <div style={{display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:'16px', marginBottom:'32px'}}>
        <div style={{background:'white', border:'1.5px solid #d8e8cf', borderRadius:'12px', padding:'20px'}}>
          <div style={{fontSize:'2rem', fontWeight:800, color:'#0f1a0a', lineHeight:1, marginBottom:'8px'}}>—</div>
          <div style={{fontSize:'0.7rem', color:'#9ca3af', textTransform:'uppercase', letterSpacing:'0.1em'}}>Markets tracked</div>
        </div>
        <div style={{background:'white', border:'1.5px solid #d8e8cf', borderRadius:'12px', padding:'20px'}}>
          <div style={{fontSize:'2rem', fontWeight:800, color:'#0f1a0a', lineHeight:1, marginBottom:'8px'}}>—</div>
          <div style={{fontSize:'0.7rem', color:'#9ca3af', textTransform:'uppercase', letterSpacing:'0.1em'}}>Alerts this month</div>
        </div>
        <div style={{background:'#e8f5ee', border:'1.5px solid #c8ecd8', borderRadius:'12px', padding:'20px'}}>
          <div style={{fontSize:'2rem', fontWeight:800, color:'#1a4d2e', lineHeight:1, marginBottom:'8px'}}>110</div>
          <div style={{fontSize:'0.7rem', color:'#6b7c63', textTransform:'uppercase', letterSpacing:'0.1em'}}>Days to Austin deadline</div>
        </div>
      </div>

      <div style={{background:'white', border:'1.5px solid #d8e8cf', borderRadius:'12px', padding:'24px'}}>
        <h2 style={{fontWeight:600, color:'#0f1a0a', marginBottom:'16px'}}>Recent Alerts</h2>
        <p style={{fontSize:'0.875rem', color:'#9ca3af'}}>No alerts yet. Add your markets to get started →</p>
      </div>
    </div>
  )
}
