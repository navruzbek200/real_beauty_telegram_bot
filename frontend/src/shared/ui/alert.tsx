import { clsx } from 'clsx'
import type { ReactNode } from 'react'

type Tone = 'success' | 'error' | 'info'

const TONE: Record<Tone, { box: string; icon: string; path: ReactNode }> = {
  success: {
    box: 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-900/20 dark:text-emerald-300',
    icon: 'text-emerald-500',
    path: <path d="m9 12 2 2 4-4M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Z" />,
  },
  error: {
    box: 'border-red-200 bg-red-50 text-red-800 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300',
    icon: 'text-red-500',
    path: <path d="M12 8v4M12 16h.01M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Z" />,
  },
  info: {
    box: 'border-brand-200 bg-brand-50 text-brand-800 dark:border-brand-900/50 dark:bg-brand-900/20 dark:text-brand-200',
    icon: 'text-brand-500',
    path: <path d="M12 16v-4M12 8h.01M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Z" />,
  },
}

interface AlertProps {
  tone?: Tone
  children: ReactNode
  onDismiss?: () => void
}

export function Alert({ tone = 'info', children, onDismiss }: AlertProps) {
  const t = TONE[tone]
  return (
    <div className={clsx('flex items-start gap-2.5 rounded-xl border px-3.5 py-2.5 text-sm', t.box)}>
      <svg
        className={clsx('mt-0.5 shrink-0', t.icon)}
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {t.path}
      </svg>
      <div className="min-w-0 flex-1 leading-relaxed">{children}</div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Yopish"
          className="-mr-1 shrink-0 rounded p-0.5 opacity-60 transition-opacity hover:opacity-100"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      )}
    </div>
  )
}
