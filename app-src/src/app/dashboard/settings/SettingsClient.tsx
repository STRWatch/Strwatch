'use client'

import { useState, useTransition } from 'react'
import { savePreferences } from './actions'

export default function SettingsClient({
  userId, phone: initialPhone, smsEnabled: initialSms, emailEnabled: initialEmail, isPro, tier,
}: {
  userId: string; phone: string; smsEnabled: boolean; emailEnabled: boolean; isPro: boolean; tier: string;
}) {
  const [phone, setPhone] = useState(initialPhone)
  const [smsEnabled, setSmsEnabled] = useState(initialSms)
  const [emailEnabled, setEmailEnabled] = useState(initialEmail)
  const [isPending, startTransition] = useTransition()
  const [feedback, setFeedback] = useState('')
  const [saved, setSaved] = useState(false)

  function formatPhone(value: string): string {
    const digits = value.replace(/\D/g, '')
    if (digits.length <= 3) return digits
    if (digits.length <= 6) return `(${digits.slice(0, 3)}) ${digits.slice(3)}`
    return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6, 10)}`
  }

  function handlePhoneChange(value: string) {
    const digits = value.replace(/\D/g, '')
    if (digits.length <= 10) {
      setPhone(formatPhone(value))
      setSaved(false)
    }
  }

  function handleSave() {
    const digits = phone.replace(/\D/g, '')
    if (smsEnabled && digits.length > 0 && digits.length !== 10) {
      setFeedback('Enter a valid 10-digit US phone number')
      setTimeout(() => setFeedback(''), 3000)
      return
    }

    const phoneE164 = digits.length === 10 ? `+1${digits}` : ''

    startTransition(async () => {
      const res = await savePreferences(userId, phoneE164, smsEnabled, emailEnabled)
      if (res.ok) {
        setSaved(true)
        setFeedback('Settings saved ✓')
        setTimeout(() => setFeedback(''), 3000)
      } else {
        setFeedback('Failed to save — try again')
        setTimeout(() => setFeedback(''), 3000)
      }
    })
  }

  return (
    <div>
      <h1 style={{fontFamily:'var(--font-syne)',fontWeight:800,fontSize:'1.6rem',color:'var(--ink)',marginBottom:'4px',letterSpacing:'-0.02em'}}>Settings</h1>
      <p style={{fontSize:'0.875rem',color:'var(--text-muted)',marginBottom:'32px'}}>Manage your notification preferences and contact info.</p>

      <div style={{background:'white',border:'1.5px solid var(--border)',borderRadius:'12px',overflow:'hidden'}}>
        {/* Notification preferences header */}
        <div style={{padding:'20px 24px',borderBottom:'1px solid var(--border)'}}>
          <div style={{fontFamily:'var(--font-syne)',fontWeight:700,fontSize:'0.95rem',color:'var(--ink)',marginBottom:'2px'}}>Notification Preferences</div>
          <div style={{fontFamily:'var(--font-mono)',fontSize:'0.58rem',color:'var(--text-faint)',letterSpacing:'0.05em'}}>Choose how you want to receive regulation alerts</div>
        </div>

        {/* Email toggle */}
        <div style={{padding:'18px 24px',borderBottom:'1px solid var(--border)',display:'flex',alignItems:'center',justifyContent:'space-between'}}>
          <div>
            <div style={{fontFamily:'var(--font-syne)',fontWeight:600,fontSize:'0.88rem',color:'var(--ink)',marginBottom:'2px'}}>Email alerts</div>
            <div style={{fontSize:'0.78rem',color:'var(--text-muted)'}}>Receive regulation change alerts via email</div>
          </div>
          <label style={{position:'relative',display:'inline-block',width:'44px',height:'24px',cursor:'pointer'}}>
            <input
              type="checkbox"
              checked={emailEnabled}
              onChange={e => { setEmailEnabled(e.target.checked); setSaved(false) }}
              style={{opacity:0,width:0,height:0}}
            />
            <span style={{
              position:'absolute',inset:0,borderRadius:'12px',transition:'background 0.2s',
              background: emailEnabled ? '#2d7a4f' : '#bfd4b0',
            }}>
              <span style={{
                position:'absolute',top:'2px',left: emailEnabled ? '22px' : '2px',
                width:'20px',height:'20px',borderRadius:'50%',background:'white',
                transition:'left 0.2s',boxShadow:'0 1px 3px rgba(0,0,0,0.15)',
              }} />
            </span>
          </label>
        </div>

        {/* SMS toggle */}
        <div style={{padding:'18px 24px',borderBottom:'1px solid var(--border)',display:'flex',alignItems:'center',justifyContent:'space-between'}}>
          <div>
            <div style={{display:'flex',alignItems:'center',gap:'8px'}}>
              <span style={{fontFamily:'var(--font-syne)',fontWeight:600,fontSize:'0.88rem',color:'var(--ink)'}}>SMS alerts</span>
              {!isPro && (
                <span style={{fontFamily:'var(--font-mono)',fontSize:'0.52rem',letterSpacing:'0.08em',textTransform:'uppercase',padding:'2px 8px',borderRadius:'100px',background:'#fdf3e3',border:'1px solid #f5d9a0',color:'#b87d2d'}}>Pro</span>
              )}
            </div>
            <div style={{fontSize:'0.78rem',color:'var(--text-muted)'}}>
              {isPro
                ? 'Receive high-urgency alerts via text message'
                : 'Upgrade to Pro for SMS notifications'}
            </div>
          </div>
          <label style={{position:'relative',display:'inline-block',width:'44px',height:'24px',cursor: isPro ? 'pointer' : 'not-allowed',opacity: isPro ? 1 : 0.5}}>
            <input
              type="checkbox"
              checked={smsEnabled && isPro}
              onChange={e => { if (isPro) { setSmsEnabled(e.target.checked); setSaved(false) }}}
              disabled={!isPro}
              style={{opacity:0,width:0,height:0}}
            />
            <span style={{
              position:'absolute',inset:0,borderRadius:'12px',transition:'background 0.2s',
              background: (smsEnabled && isPro) ? '#2d7a4f' : '#bfd4b0',
            }}>
              <span style={{
                position:'absolute',top:'2px',left: (smsEnabled && isPro) ? '22px' : '2px',
                width:'20px',height:'20px',borderRadius:'50%',background:'white',
                transition:'left 0.2s',boxShadow:'0 1px 3px rgba(0,0,0,0.15)',
              }} />
            </span>
          </label>
        </div>

        {/* Phone number */}
        <div style={{padding:'18px 24px',borderBottom:'1px solid var(--border)'}}>
          <div style={{fontFamily:'var(--font-syne)',fontWeight:600,fontSize:'0.88rem',color:'var(--ink)',marginBottom:'2px'}}>Phone number</div>
          <div style={{fontSize:'0.78rem',color:'var(--text-muted)',marginBottom:'12px'}}>US mobile number for SMS alerts</div>
          <div style={{display:'flex',gap:'10px',alignItems:'center',maxWidth:'360px'}}>
            <span style={{fontFamily:'var(--font-mono)',fontSize:'0.85rem',color:'var(--text-faint)'}}>+1</span>
            <input
              type="tel"
              value={phone}
              onChange={e => handlePhoneChange(e.target.value)}
              placeholder="(555) 123-4567"
              disabled={!isPro}
              style={{
                flex:1,padding:'10px 14px',border:'1.5px solid var(--border-mid)',borderRadius:'8px',
                fontSize:'0.88rem',fontFamily:'var(--font-sans)',outline:'none',
                opacity: isPro ? 1 : 0.5, background: isPro ? 'white' : 'var(--off-white)',
              }}
            />
          </div>
        </div>

        {/* Save button */}
        <div style={{padding:'18px 24px',display:'flex',alignItems:'center',gap:'12px'}}>
          <button
            onClick={handleSave}
            disabled={isPending}
            style={{
              fontFamily:'var(--font-syne)',fontWeight:700,fontSize:'0.75rem',
              padding:'10px 24px',background:'var(--green-deep)',color:'white',
              borderRadius:'8px',border:'none',cursor:'pointer',
            }}
          >
            {isPending ? 'Saving...' : 'Save settings'}
          </button>
          {feedback && (
            <span style={{
              fontFamily:'var(--font-mono)',fontSize:'0.62rem',letterSpacing:'0.05em',
              color: feedback.includes('✓') ? 'var(--green)' : '#b84040',
            }}>{feedback}</span>
          )}
        </div>
      </div>
    </div>
  )
}
