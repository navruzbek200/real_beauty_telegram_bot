import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { customerApi } from '@/entities/customer'
import { supportThreadApi } from '@/entities/support'
import { skinQuizResultApi } from '@/entities/analytics'
import { broadcastApi } from '@/entities/campaign'
import { hasPermission, isSuperUser, useSessionStore } from '@/entities/session'
import { NAV_SECTIONS } from '@/widgets/app-shell'
import { Spinner } from '@/shared/ui'

interface StatDef {
  key: string
  label: string
  to: string
  permission: string
  tone: 'brand' | 'amber' | 'emerald' | 'slate'
  fetch: () => Promise<number>
}

const STAT_DEFS: StatDef[] = [
  {
    key: 'customers',
    label: 'Xaridorlar',
    to: '/customers',
    permission: 'users.view_telegramuser',
    tone: 'brand',
    fetch: () => customerApi.list({ page: 1, page_size: 1 }).then((r) => r.count),
  },
  {
    key: 'awaiting',
    label: 'Javob kutayotgan murojaatlar',
    to: '/support-threads',
    permission: 'support.view_supportthread',
    tone: 'amber',
    fetch: () =>
      supportThreadApi
        .list({ page: 1, page_size: 1, awaiting_reply: 'true' } as never)
        .then((r) => r.count),
  },
  {
    key: 'quiz',
    label: 'Teri testi natijalari',
    to: '/skin-quiz-results',
    permission: 'analytics.view_skinquizresult',
    tone: 'emerald',
    fetch: () => skinQuizResultApi.list({ page: 1, page_size: 1 }).then((r) => r.count),
  },
  {
    key: 'broadcasts',
    label: "E'lonlar",
    to: '/broadcasts',
    permission: 'campaigns.view_broadcast',
    tone: 'slate',
    fetch: () => broadcastApi.list({ page: 1, page_size: 1 }).then((r) => r.count),
  },
]

const TONE_ACCENT: Record<StatDef['tone'], string> = {
  brand: 'text-brand-600 dark:text-brand-400',
  amber: 'text-amber-600 dark:text-amber-400',
  emerald: 'text-emerald-600 dark:text-emerald-400',
  slate: 'text-slate-600 dark:text-slate-300',
}

function StatCard({ def }: { def: StatDef }) {
  const query = useQuery({
    queryKey: ['dashboard-stat', def.key],
    queryFn: def.fetch,
    staleTime: 60_000,
  })
  return (
    <Link
      to={def.to}
      className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-md dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700"
    >
      <p className="text-sm text-slate-500 dark:text-slate-400">{def.label}</p>
      <div className="mt-2 flex items-end justify-between">
        {query.isLoading ? (
          <Spinner className="h-6 w-6" />
        ) : query.isError ? (
          <span className="text-2xl font-semibold text-slate-300">—</span>
        ) : (
          <span className={`text-3xl font-semibold tracking-tight ${TONE_ACCENT[def.tone]}`}>
            {query.data}
          </span>
        )}
        <span className="text-slate-300 transition-colors group-hover:text-slate-500 dark:text-slate-600">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12h14M13 6l6 6-6 6" />
          </svg>
        </span>
      </div>
    </Link>
  )
}

export function DashboardPage() {
  const user = useSessionStore((s) => s.user)
  const stats = STAT_DEFS.filter((s) => hasPermission(user, s.permission))

  const navLinks = NAV_SECTIONS.flatMap((section) => section.items)
    .filter((item) => item.to !== '/')
    .filter((item) => {
      if (item.superuserOnly) return isSuperUser(user)
      if (item.permission) return hasPermission(user, item.permission)
      return true
    })

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
          Xush kelibsiz, {user?.username} 👋
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Do'koningiz holatining qisqacha ko'rinishi.
        </p>
      </div>

      {stats.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((def) => (
            <StatCard key={def.key} def={def} />
          ))}
        </div>
      )}

      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
          Tezkor havolalar
        </h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {navLinks.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200 dark:hover:border-brand-800 dark:hover:bg-brand-900/20"
            >
              {item.label}
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
