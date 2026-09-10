import { clsx } from 'clsx'

export interface TabItem {
  key: string
  label: string
}

interface TabsProps {
  tabs: TabItem[]
  active: string
  onChange: (key: string) => void
}

/**
 * A simple underline tab strip. Kept presentational — the active key lives in
 * the page (usually mirrored to the URL) so a reload lands on the same tab.
 */
export function Tabs({ tabs, active, onChange }: TabsProps) {
  return (
    <div
      role="tablist"
      className="flex gap-1 border-b border-slate-200 dark:border-slate-800"
    >
      {tabs.map((tab) => {
        const selected = tab.key === active
        return (
          <button
            key={tab.key}
            role="tab"
            aria-selected={selected}
            onClick={() => onChange(tab.key)}
            className={clsx(
              'cursor-pointer border-b-2 px-4 py-2 text-sm font-medium transition-colors -mb-px',
              selected
                ? 'border-brand-600 text-brand-700 dark:border-brand-400 dark:text-brand-300'
                : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200',
            )}
          >
            {tab.label}
          </button>
        )
      })}
    </div>
  )
}
