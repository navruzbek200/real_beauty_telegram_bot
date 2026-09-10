import type { ReactNode } from 'react'

interface EmptyStateProps {
  message: string
  hint?: string
  tone?: 'default' | 'error'
  action?: ReactNode
}

export function EmptyState({ message, hint, tone = 'default', action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-slate-200 bg-white/50 px-6 py-14 text-center dark:border-slate-800 dark:bg-slate-900/40">
      <div
        className={`flex h-12 w-12 items-center justify-center rounded-full ${
          tone === 'error'
            ? 'bg-red-100 text-red-500 dark:bg-red-900/40 dark:text-red-400'
            : 'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500'
        }`}
      >
        {tone === 'error' ? (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 8v4M12 16h.01" />
          </svg>
        ) : (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 7v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-6l-2-2H5a2 2 0 0 0-2 2Z" />
          </svg>
        )}
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium text-slate-600 dark:text-slate-300">{message}</p>
        {hint && <p className="text-xs text-slate-400 dark:text-slate-500">{hint}</p>}
      </div>
      {action}
    </div>
  )
}
