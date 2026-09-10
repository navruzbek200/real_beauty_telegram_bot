import type { ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  count?: number
  countLabel?: string
  description?: string
  actions?: ReactNode
}

export function PageHeader({ title, count, countLabel = 'ta', description, actions }: PageHeaderProps) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <div className="flex items-center gap-2">
          {title && (
            <h1 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">{title}</h1>
          )}
          {typeof count === 'number' && (
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500 dark:bg-slate-800 dark:text-slate-400">
              {count} {countLabel}
            </span>
          )}
        </div>
        {description && <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}
