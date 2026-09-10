import type { ResourceColumn } from '@/shared/lib/resource-crud-types'
import { Badge } from '@/shared/ui'
import type { SkinQuizResult } from '@/entities/analytics'

const SKIN_TONE: Record<string, 'neutral' | 'success' | 'warning' | 'info'> = {
  dry: 'warning',
  oily: 'info',
  combined: 'neutral',
  normal: 'success',
  sensitive: 'warning',
}

export const skinQuizResultColumns: ResourceColumn<SkinQuizResult>[] = [
  {
    key: 'user_name',
    header: 'Mijoz',
    render: (r) => (r.user_name as string) || `#${r.user}`,
  },
  {
    key: 'phone_number',
    header: 'Telefon',
    render: (r) => (r.phone_number as string) || '—',
  },
  {
    key: 'skin_type',
    header: 'Teri turi',
    render: (r) => (
      <Badge tone={SKIN_TONE[r.skin_type as string] ?? 'neutral'}>
        {(r.skin_type_display as string) || r.skin_type}
      </Badge>
    ),
  },
  {
    key: 'recommendations',
    header: 'Tavsiyalar',
    render: (r) => {
      const recs = (r.recommendations as string[] | undefined) ?? []
      return recs.length ? `${recs.length} ta blok` : '—'
    },
  },
  {
    key: 'created_at',
    header: 'Vaqt',
    sortField: 'created_at',
    render: (r) => new Date(r.created_at as string).toLocaleString('uz-UZ'),
  },
]
