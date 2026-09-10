import { clsx } from 'clsx'

import { useCopy } from '@/shared/lib/use-copy'

function CopyIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="9" y="9" width="11" height="11" rx="2" />
      <path d="M5 15V5a2 2 0 0 1 2-2h10" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  )
}

/**
 * Copy a code with one click, and say so.
 *
 * An access code is read off this screen and typed into a phone. Selecting
 * it by hand is where a seller drops a character, so every place a code
 * appears is a place it should be copyable — not only the moment it was
 * minted.
 */
export function CopyableCode({
  value,
  size = 'sm',
}: {
  value: string
  size?: 'sm' | 'lg'
}) {
  const { copied, copy } = useCopy()
  const isCopied = copied === value

  return (
    <button
      type="button"
      onClick={() => copy(value)}
      // The label carries the state so a screen reader hears the result too,
      // not just the icon swap.
      aria-label={isCopied ? `${value} nusxa olindi` : `${value} — nusxa olish`}
      title={isCopied ? 'Nusxa olindi' : 'Nusxa olish'}
      className={clsx(
        'group inline-flex items-center gap-2 rounded-lg border font-mono font-bold tracking-widest transition',
        size === 'lg' ? 'px-3 py-2 text-base' : 'px-2 py-1 text-sm',
        isCopied
          ? 'border-emerald-500 bg-emerald-50 text-emerald-700 dark:border-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-300'
          : 'border-slate-200 text-brand-700 hover:border-brand-400 hover:bg-brand-50 dark:border-slate-700 dark:text-brand-300 dark:hover:border-brand-600 dark:hover:bg-brand-950/40',
      )}
    >
      <span>{value}</span>
      <span className={clsx('shrink-0', isCopied ? 'opacity-100' : 'opacity-40 group-hover:opacity-80')}>
        {isCopied ? <CheckIcon /> : <CopyIcon />}
      </span>
    </button>
  )
}
