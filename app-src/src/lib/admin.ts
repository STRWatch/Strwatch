import { auth } from '@clerk/nextjs/server'
import { redirect } from 'next/navigation'

function getAdminIds(): string[] {
  const raw = process.env.ADMIN_USER_IDS || ''
  return raw.split(',').map(id => id.trim()).filter(Boolean)
}

export async function requireAdmin(): Promise<string> {
  const { userId } = await auth()
  if (!userId) redirect('/sign-in')
  const ids = getAdminIds()
  if (ids.length === 0 || !ids.includes(userId)) redirect('/dashboard')
  return userId
}

export async function isAdmin(): Promise<boolean> {
  const { userId } = await auth()
  if (!userId) return false
  const ids = getAdminIds()
  return ids.length > 0 && ids.includes(userId)
}
