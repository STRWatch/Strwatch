'use client'

import { useState, useTransition } from 'react'
import { addDeadline, removeDeadline } from './actions'

const CATEGORY_LABELS: Record<string, {label:string;bg:string;border:string;text:string}> = {
  permit:       {label:'Permit',bg:'#eef3ff',border:'#c8d8f7',text:'#3a5cb8'},
  enforcement:  {label:'Enforcement',bg:'#fff0ee',border:'#f7c8c8',text:'#b84040'},
  legislation:  {label:'Legislation',bg:'#fdf3e3',border:'#f5d9a0',text:'#b87d2d'},
  custom:       {label:'Custom',bg:'#f3eeff',border:'#d4c2f5',text:'#6b3fb8'},
}

function getUrgency(dateStr: string): {label:string;bg:string;border:string;text:string} {
  const now = new Date()
  const deadline = new Date(dateStr + 'T00:00:00')
  const days = Math.ceil((deadline.getTime() - now.getTime()) / 86400000)
  if (days < 0) return {label:`${Math.abs(days)}d overdue`,bg:'#fff0ee',border:'#f7c8c8',text:'#b84040'}
  if (days <= 30) return {label:`${days}d left`,bg:'#fff0ee',border:'#f7c8c8',text:'#b84040'}
  if (days <= 90) return {label:`${days}d left`,bg:'#fdf3e3',border:'#f5d9a0',text:'#b87d2d'}
  return {label:`${days}d left`,bg:'#e8f5ee',border:'#c8ecd8',text:'#2d7a4f'}
}

export default function DeadlinesClient({
  userId, deadlines: initialDeadlines, userCities,
}: {
  userId: string; deadlines: any[]; userCities: string[];
}) {
  const [deadlines, setDeadlines] = useState(initialDeadlines)
  const [isPending, startTransition] = useTransition()
  const [showForm, setShowForm] = useState(false)
  const [formCity, setFormCity] = useState(userCities[0] || '')
  const [formTitle, setFormTitle] = useState('')
  const [formDate, setFormDate] = useState('')
  const [formDesc, setFormDesc] = useState('')
  const [feedback, setFeedback] = useState('')

  function handleAdd() {
    if (!formTitle || !formDate || !formCity) {
      setFeedback('Fill in title, date, and city')
      setTimeout(() => setFeedback(''), 3000)
      return
    }
    const optimistic = {
      id: 'temp-' + Date.now(),
      city: formCity,
      title: formTitle,
      deadline_date: formDate,
      description: formDesc,
      category: 'custom',
      user_id: userId,
      source_url: null,
    }
    setDeadlines(prev => [...prev, optimistic].sort((a, b) => a.deadline_date.localeCompare(b.deadline_date)))
    setFormTitle('')
    setFormDate('')
    setFormDesc('')
    setShowForm(false)

    startTransition(async () => {
      const res = await addDeadline(userId, formCity, formTitle || optimistic.title, formDate || optimistic.deadline_date, formDesc)
      if (!res.ok) {
        setDeadlines(prev => prev.filter(d => d.id !== optimistic.id))
        setFeedback('Failed to save — try again')
        setTimeout(() => setFeedback(''), 3000)
      }
    })
  }

  function handleRemove(id: string) {
    const removed = deadlines.find(d => d.id === id)
    setDeadlines(prev => prev.filter(d => d.id !== id))
    startTransition(async () => {
      const res = await removeDeadline(userId, id)
      if (!res.ok && removed) {
        setDeadlines(prev => [...prev, removed].sort((a, b) => a.deadline_date.localeCompare(b.deadline_date)))
      }
    })
  }

  return (
    <div>
      <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:'32px'}}>
        <div>
          <h1 style={{fontFamily:'var(--font-syne)',fontWeight:800,fontSize:'1.6rem',color:'var(--ink)',marginBottom:'4px',letterSpacing:'-0.02em'}}>Permit Deadlines</h1>
          <p style={{fontSize:'0.875rem',color:'var(--text-muted)'}}>Upcoming deadlines and renewal dates for your markets.</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          style={{fontFamily:'var(--font-syne)',fontWeight:700,fontSize:'0.75rem',padding:'10px 20px',background:showForm ? 'var(--border)' : 'var(--green-deep)',color:showForm ? 'var(--ink)' : 'white',borderRadius:'8px',border:'none',cursor:'pointer',whiteSpace:'nowrap'}}
        >
          {showForm ? 'Cancel' : '+ Add deadline'}
        </button>
      </div>

      {/* Add deadline form */}
      {showForm && (
        <div style={{background:'white',border:'1.5px solid var(--green-light)',borderRadius:'12px',padding:'20px 24px',marginBottom:'24px'}}>
          <div style={{fontFamily:'var(--font-mono)',fontSize:'0.6rem',letterSpacing:'0.15em',textTransform:'uppercase',color:'var(--green)',marginBottom:'14px'}}>Add custom deadline</div>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'12px',marginBottom:'12px'}}>
            <div>
              <label style={{fontFamily:'var(--font-mono)',fontSize:'0.58rem',color:'var(--text-faint)',letterSpacing:'0.05em',display:'block',marginBottom:'4px'}}>Title *</label>
              <input
                type="text"
                value={formTitle}
                onChange={e => setFormTitle(e.target.value)}
                placeholder="e.g. Nashville permit renewal"
                style={{width:'100%',padding:'10px 14px',border:'1.5px solid var(--border-mid)',borderRadius:'8px',fontSize:'0.85rem',fontFamily:'var(--font-sans)',outline:'none'}}
              />
            </div>
            <div>
              <label style={{fontFamily:'var(--font-mono)',fontSize:'0.58rem',color:'var(--text-faint)',letterSpacing:'0.05em',display:'block',marginBottom:'4px'}}>Deadline date *</label>
              <input
                type="date"
                value={formDate}
                onChange={e => setFormDate(e.target.value)}
                style={{width:'100%',padding:'10px 14px',border:'1.5px solid var(--border-mid)',borderRadius:'8px',fontSize:'0.85rem',fontFamily:'var(--font-sans)',outline:'none'}}
              />
            </div>
          </div>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'12px',marginBottom:'16px'}}>
            <div>
              <label style={{fontFamily:'var(--font-mono)',fontSize:'0.58rem',color:'var(--text-faint)',letterSpacing:'0.05em',display:'block',marginBottom:'4px'}}>City *</label>
              <select
                value={formCity}
                onChange={e => setFormCity(e.target.value)}
                style={{width:'100%',padding:'10px 14px',border:'1.5px solid var(--border-mid)',borderRadius:'8px',fontSize:'0.85rem',fontFamily:'var(--font-sans)',outline:'none',background:'white'}}
              >
                {userCities.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label style={{fontFamily:'var(--font-mono)',fontSize:'0.58rem',color:'var(--text-faint)',letterSpacing:'0.05em',display:'block',marginBottom:'4px'}}>Notes (optional)</label>
              <input
                type="text"
                value={formDesc}
                onChange={e => setFormDesc(e.target.value)}
                placeholder="e.g. Permit #STRP-2024-1234"
                style={{width:'100%',padding:'10px 14px',border:'1.5px solid var(--border-mid)',borderRadius:'8px',fontSize:'0.85rem',fontFamily:'var(--font-sans)',outline:'none'}}
              />
            </div>
          </div>
          <div style={{display:'flex',alignItems:'center',gap:'12px'}}>
            <button
              onClick={handleAdd}
              disabled={isPending}
              style={{fontFamily:'var(--font-syne)',fontWeight:700,fontSize:'0.75rem',padding:'10px 24px',background:'var(--green-deep)',color:'white',borderRadius:'8px',border:'none',cursor:'pointer'}}
            >
              {isPending ? 'Saving...' : 'Save deadline'}
            </button>
            {feedback && <span style={{fontFamily:'var(--font-mono)',fontSize:'0.6rem',color:'#b87d2d'}}>{feedback}</span>}
          </div>
        </div>
      )}

      {/* Empty state */}
      {userCities.length === 0 ? (
        <div style={{background:'white',border:'1.5px solid var(--border)',borderRadius:'12px',padding:'48px 20px',textAlign:'center'}}>
          <p style={{fontFamily:'var(--font-mono)',fontSize:'0.65rem',letterSpacing:'0.08em',color:'var(--text-faint)'}}>
            No markets added yet. <a href="/dashboard/markets" style={{color:'var(--green)'}}>Add your markets →</a> to see upcoming deadlines.
          </p>
        </div>
      ) : deadlines.length === 0 ? (
        <div style={{background:'white',border:'1.5px solid var(--border)',borderRadius:'12px',padding:'48px 20px',textAlign:'center'}}>
          <p style={{fontFamily:'var(--font-mono)',fontSize:'0.65rem',letterSpacing:'0.08em',color:'var(--text-faint)'}}>
            No deadlines yet. Click &quot;+ Add deadline&quot; to track your permit renewals and compliance dates.
          </p>
        </div>
      ) : (
        <div style={{display:'flex',flexDirection:'column',gap:'12px'}}>
          {deadlines.map((d: any) => {
            const urgency = getUrgency(d.deadline_date)
            const cat = CATEGORY_LABELS[d.category] || CATEGORY_LABELS.permit
            const isCustom = d.user_id !== null && d.user_id !== undefined
            return (
              <div key={d.id} style={{background:'white',border:`1.5px solid ${isCustom ? '#d4c2f5' : 'var(--border)'}`,borderRadius:'12px',padding:'20px 24px',display:'flex',gap:'16px',alignItems:'flex-start'}}>
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

                {/* Delete button for custom deadlines */}
                {isCustom && (
                  <button
                    onClick={() => handleRemove(d.id)}
                    disabled={isPending}
                    style={{fontFamily:'var(--font-mono)',fontSize:'0.58rem',letterSpacing:'0.1em',textTransform:'uppercase',color:'var(--text-faint)',background:'none',border:'none',cursor:'pointer',padding:'4px 8px',flexShrink:0}}
                    title="Remove deadline"
                  >
                    Remove
                  </button>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
