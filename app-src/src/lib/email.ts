import { Resend } from 'resend'
import { appUrl } from '@/lib/url'

export const EMAIL_FROM = 'Pete at STRWatch <alerts@strwatch.io>'
export const EMAIL_REPLY_TO = 'peter@strwatch.io'

export type EmailTemplate = { subject: string; text: string; html: string }

export type LifecycleTemplate = 'day35' | 'day45' | 'day50'

function settingsUrl(): string {
  return `${appUrl()}/dashboard/settings`
}

function foundingUpgradeUrl(): string {
  return `${settingsUrl()}?upgrade=founding`
}

export type LifecycleContext = { foundingMember: boolean }

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

/** Plain text paragraphs -> minimal HTML. Bare URLs become links. */
function toHtml(text: string): string {
  const paragraphs = text.trim().split(/\n\s*\n/)
  const body = paragraphs
    .map(p => {
      const escaped = escapeHtml(p).replace(/\n/g, '<br>')
      const linked = escaped.replace(
        /(https?:\/\/[^\s<]+)/g,
        '<a href="$1" style="color:#1a4d2e">$1</a>'
      )
      return `<p style="margin:0 0 16px">${linked}</p>`
    })
    .join('\n')
  return `<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;font-size:15px;line-height:1.6;color:#1a1a1a;max-width:560px">\n${body}\n</div>`
}

function template(subject: string, text: string): EmailTemplate {
  return { subject, text: text.trim() + '\n', html: toHtml(text) }
}

/** Day 35: 10 days left on the trial. Founding members get the $19 locked offer. */
export function day35Email({ foundingMember }: LifecycleContext): EmailTemplate {
  if (foundingMember) {
    return template(
      'Your STRWatch trial ends in 10 days',
      `Hi,

Quick heads up from me: your Pro trial on STRWatch ends in 10 days.

You signed up early, so I want to make you an offer I am not going to make later. Pro is $29 a month at list. For early users I am locking it at $19 a month, for as long as you keep the subscription. That price never goes up.

If STRWatch has caught something useful for you, or you just want to keep real-time alerts across all your markets, you can lock the founding price here:

${foundingUpgradeUrl()}

If it has not been useful, no hard feelings. Reply and tell me what was missing. I read every one of these.

Pete
STRWatch`
    )
  }
  return template(
    'Your STRWatch trial ends in 10 days',
    `Hi,

Quick heads up from me: your Pro trial on STRWatch ends in 10 days.

After that your account moves to the Free plan: one market and a weekly digest. Pro is $29 a month and keeps all your markets, real-time alerts, SMS, and market scans.

If STRWatch has caught something useful for you, you can upgrade from your settings page:

${settingsUrl()}

If it has not been useful, no hard feelings. Reply and tell me what was missing. I read every one of these.

Pete
STRWatch`
  )
}

/** Day 45: trial over, account moved to Free. */
export function day45Email(_ctx: LifecycleContext): EmailTemplate {
  const link = settingsUrl()
  return template(
    'Your STRWatch trial has ended',
    `Hi,

Your Pro trial ended today, so I have moved your account to the Free plan.

Free still works. You keep one market and a weekly digest of regulation changes there, so you will not miss anything big. What you lose is the rest of your markets, real-time alerts, SMS, and market scans.

If you want those back, you can upgrade any time from your settings page:

${link}

Either way, thanks for trying it. If something about the trial fell flat, hit reply and tell me. It helps more than you would think.

Pete
STRWatch`
  )
}

/** Day 50: honest ask for feedback from someone who did not convert. */
export function day50Email(_ctx: LifecycleContext): EmailTemplate {
  return template(
    'One honest question',
    `Hi,

Your trial ended a few days ago and you did not upgrade. That is fine, and this is not a sales email.

I am building STRWatch mostly on my own, and the most useful thing I can get right now is a straight answer from someone who tried it and walked. So, one question: what would have made you stay?

Maybe it was the price, maybe a market I do not cover yet, maybe the alerts were noise, maybe you just did not need it. Whatever it is, I would rather hear it than guess.

Just reply to this email. It comes straight to me and I answer every one.

Thanks for giving it a shot.

Pete
STRWatch`
  )
}

export const LIFECYCLE_TEMPLATES: Record<LifecycleTemplate, (ctx: LifecycleContext) => EmailTemplate> = {
  day35: day35Email,
  day45: day45Email,
  day50: day50Email,
}

/** Which lifecycle emails a user is due, given days since trial start and current tier. */
export function dueTemplates(daysSinceStart: number, tier: string): LifecycleTemplate[] {
  const due: LifecycleTemplate[] = []
  if (daysSinceStart >= 35) due.push('day35')
  if (daysSinceStart >= 45 && tier === 'free') due.push('day45')
  if (daysSinceStart >= 50 && tier === 'free') due.push('day50')
  return due
}

/** Resend client. Env read per call so `next build` never needs the key. */
function getResend(): Resend {
  const apiKey = process.env.RESEND_API_KEY
  if (!apiKey) throw new Error('Missing required environment variable: RESEND_API_KEY')
  return new Resend(apiKey)
}

export async function sendEmail(to: string, email: EmailTemplate): Promise<void> {
  const resend = getResend()
  const { error } = await resend.emails.send({
    from: EMAIL_FROM,
    to,
    replyTo: EMAIL_REPLY_TO,
    subject: email.subject,
    text: email.text,
    html: email.html,
  })
  if (error) throw new Error(`Resend error: ${error.name}: ${error.message}`)
}
