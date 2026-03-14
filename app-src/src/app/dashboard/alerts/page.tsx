import { auth } from '@clerk/nextjs/server'
import { redirect } from 'next/navigation'

export default async function AlertsPage() {
  const { userId } = await auth()
  if (!userId) redirect('/sign-in')

  return (
    <div>
      <h1 className="text-2xl font-bold text-[var(--ink)] mb-2">Alert History</h1>
      <p className="text-gray-500 mb-8">All regulation changes detected for your markets.</p>

      <div className="bg-white border border-[var(--border)] rounded-xl p-6">
        <p className="text-sm text-gray-400">No alerts yet.</p>
      </div>
    </div>
  )
}
