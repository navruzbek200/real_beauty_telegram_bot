import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'

import { hasPermission, isSuperUser, useSessionStore } from '@/entities/session'
import { Button } from '@/shared/ui'
import { NAV_SECTIONS } from '../model/nav'

export function AppShell({ children }: { children: ReactNode }) {
  const user = useSessionStore((s) => s.user)
  const logout = useSessionStore((s) => s.logout)

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-slate-950">
      <aside className="flex w-64 shrink-0 flex-col border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center gap-2.5 border-b border-slate-200 px-4 py-4 dark:border-slate-800">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-sm font-bold text-white">
            RB
          </span>
          <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Real Beauty CRM</p>
        </div>
        <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4">
          {NAV_SECTIONS.map((section) => {
            const items = section.items.filter((item) => {
              if (item.superuserOnly) return isSuperUser(user)
              if (item.permission) return hasPermission(user, item.permission)
              return true
            })
            if (items.length === 0) return null
            return (
              <div key={section.title}>
                <p className="mb-1 px-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  {section.title}
                </p>
                {items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === '/'}
                    className={({ isActive }) =>
                      `block rounded-lg px-2.5 py-2 text-sm transition-colors ${
                        isActive
                          ? 'bg-brand-50 font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-300'
                          : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
                      }`
                    }
                  >
                    {item.label}
                  </NavLink>
                ))}
              </div>
            )
          })}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white/80 px-6 py-3 backdrop-blur dark:border-slate-800 dark:bg-slate-900/80">
          <span className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold uppercase text-slate-500 dark:bg-slate-800 dark:text-slate-300">
              {user?.username?.[0] ?? '?'}
            </span>
            <span className="font-medium">{user?.username}</span>
            <span className="hidden text-slate-400 sm:inline">
              {user?.is_superuser ? 'Administrator' : 'Sotuvchi'}
            </span>
          </span>
          <Button variant="secondary" size="sm" onClick={logout}>
            Chiqish
          </Button>
        </header>
        <main className="flex-1 overflow-x-hidden p-6">{children}</main>
      </div>
    </div>
  )
}
