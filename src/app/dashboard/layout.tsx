import { UserButton } from '@clerk/nextjs'
import Link from 'next/link'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{minHeight:'100vh', background:'#f7f9f5'}}>
      <nav style={{
        height:'56px',
        background:'white',
        borderBottom:'1px solid #d8e8cf',
        display:'flex',
        alignItems:'center',
        justifyContent:'space-between',
        padding:'0 24px',
        position:'fixed',
        top:0, left:0, right:0,
        zIndex:50,
        boxShadow:'0 1px 3px rgba(0,0,0,0.06)'
      }}>
        <div style={{display:'flex', alignItems:'center', gap:'32px'}}>
          <Link href="/dashboard" style={{fontWeight:800, fontSize:'1.1rem', color:'#0f1a0a', textDecoration:'none', letterSpacing:'-0.02em'}}>
            STR<span style={{color:'#2d7a4f'}}>Watch</span>
          </Link>
          <Link href="/dashboard" style={{fontSize:'0.875rem', color:'#6b7280', textDecoration:'none'}}>Overview</Link>
          <Link href="/dashboard/markets" style={{fontSize:'0.875rem', color:'#6b7280', textDecoration:'none'}}>Markets</Link>
          <Link href="/dashboard/alerts" style={{fontSize:'0.875rem', color:'#6b7280', textDecoration:'none'}}>Alerts</Link>
        </div>
        <UserButton afterSignOutUrl="/sign-in" />
      </nav>
      <main style={{paddingTop:'80px', padding:'80px 32px 32px', maxWidth:'960px', margin:'0 auto'}}>
        {children}
      </main>
    </div>
  )
}