import { useQuery } from '@tanstack/react-query'

import { ResourcePage } from '@/widgets/resource-crud'
import { customerApi } from '@/entities/customer'
import { lessonUnlockApi, type LessonUnlock } from '@/entities/lesson'
import {
  buildLessonUnlockFormConfig,
  lessonUnlockColumns,
  toLessonUnlockPayload,
  type LessonUnlockFormValues,
} from '@/features/lesson'

export function LessonUnlocksPage() {
  const { data: customers } = useQuery({
    queryKey: ['customers', 'for-unlock'],
    queryFn: () => customerApi.list({ page_size: 200 }),
  })

  const options = (customers?.results ?? []).map((c) => ({
    value: String(c.id),
    label: c.full_name || String(c.telegram_id ?? c.id),
  }))

  return (
    <ResourcePage<LessonUnlock, LessonUnlockFormValues, Record<string, unknown>, Record<string, unknown>>
      title="Kim darslarni ochgan"
      api={lessonUnlockApi}
      queryKey={['lesson-unlocks']}
      columns={lessonUnlockColumns}
      searchPlaceholder="Xaridor yoki kalit bo'yicha qidirish..."
      permissions={{
        add: 'lessons.add_lessonunlock',
        delete: 'lessons.delete_lessonunlock',
      }}
      formConfig={buildLessonUnlockFormConfig(options)}
      toCreatePayload={toLessonUnlockPayload}
      createLabel="+ Qo'lda ochish"
    />
  )
}
