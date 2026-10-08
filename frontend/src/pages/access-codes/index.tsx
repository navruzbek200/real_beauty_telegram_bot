import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'

import { ResourcePage } from '@/widgets/resource-crud'
import { Button, CopyableCode, Select } from '@/shared/ui'
import { useCopy } from '@/shared/lib/use-copy'
import { hasPermission, useSessionStore } from '@/entities/session'
import { accessCodeApi, type AccessCode } from '@/entities/lesson'
import {
  accessCodeColumns,
  accessCodeFormConfig,
  toAccessCodePayload,
  type AccessCodeFormValues,
} from '@/features/lesson'

/**
 * Issuing a code is the seller's most frequent job here — one per customer who
 * just bought something — so it sits above the table as a two-tap action
 * rather than behind the "add" form, which asks for four fields they do not
 * care about.
 *
 * Fresh codes are shown once, large and copyable: a code is only useful in the
 * seconds between minting it and reading it out at the counter.
 */
function IssuePanel() {
  const queryClient = useQueryClient()
  const [count, setCount] = useState('1')
  const [fresh, setFresh] = useState<string[]>([])
  const { copied, copy } = useCopy()

  const issue = useMutation({
    mutationFn: () => accessCodeApi.issue(Number(count)),
    onSuccess: (codes) => {
      setFresh(codes)
      queryClient.invalidateQueries({ queryKey: ['access-codes'] })
    },
  })

  // A batch is usually pasted somewhere as a list — into a note, a message to
  // a colleague — so copying them one at a time is the wrong unit of work.
  const allCodes = fresh.join('\n')

  return (
    <div className="mb-4 space-y-3">
      {fresh.length > 0 && (
        <div className="rounded-xl border border-emerald-300 bg-emerald-50 p-4 dark:border-emerald-800 dark:bg-emerald-950/40">
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <p className="mr-auto text-sm text-slate-700 dark:text-slate-200">
              <b>{fresh.length} ta kod tayyor</b>
              <span className="text-slate-500 dark:text-slate-400">
                {' '}
                — kodning ustiga bosing, nusxa olinadi
              </span>
            </p>
            {fresh.length > 1 && (
              <Button variant="ghost" onClick={() => copy(allCodes)}>
                {copied === allCodes ? '✓ Nusxa olindi' : 'Hammasini nusxa olish'}
              </Button>
            )}
            <Button variant="ghost" onClick={() => setFresh([])}>
              Yopish
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {fresh.map((code) => (
              <CopyableCode key={code} value={code} size="lg" />
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-800 dark:bg-slate-900/60">
        <div className="mr-auto">
          <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
            Yangi kod chiqarish
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Har bir kod <b>bitta mijozga</b> ishlaydi. Xarid qilgan mijozga bering.
          </p>
        </div>
        <Select value={count} onChange={(e) => setCount(e.target.value)} className="max-w-24">
          <option value="1">1 ta</option>
          <option value="5">5 ta</option>
          <option value="10">10 ta</option>
          <option value="25">25 ta</option>
        </Select>
        <Button onClick={() => issue.mutate()} disabled={issue.isPending}>
          {issue.isPending ? 'Chiqarilmoqda…' : 'Chiqarish'}
        </Button>
      </div>
    </div>
  )
}

export function AccessCodesPage() {
  const user = useSessionStore((s) => s.user)
  const canAdd = hasPermission(user, 'lessons.add_accesscode')

  return (
    <>
      {canAdd && <IssuePanel />}
      <ResourcePage<AccessCode, AccessCodeFormValues, Record<string, unknown>, Record<string, unknown>>
        title="Kalit so'zlar"
        api={accessCodeApi}
        queryKey={['access-codes']}
        columns={accessCodeColumns}
        filterKeys={['state']}
        searchPlaceholder="Kalit so'z yoki izoh bo'yicha qidirish..."
        permissions={{
          add: 'lessons.add_accesscode',
          change: 'lessons.change_accesscode',
          delete: 'lessons.delete_accesscode',
        }}
        formConfig={accessCodeFormConfig}
        toCreatePayload={toAccessCodePayload}
        toUpdatePayload={toAccessCodePayload}
        filterBar={(state) => (
          <Select
            value={state.filters.state ?? ''}
            onChange={(e) => state.setFilter('state', e.target.value || null)}
            className="max-w-56"
          >
            <option value="">Barcha holatlar</option>
            <option value="free">🟢 Berish mumkin</option>
            <option value="used">✔️ Ishlatilgan</option>
            <option value="expired">Muddati tugagan</option>
            <option value="off">O&apos;chirilgan</option>
          </Select>
        )}
      />
    </>
  )
}
