import { ResourcePage } from '@/widgets/resource-crud'
import { skinQuizResultApi, type SkinQuizResult } from '@/entities/analytics'
import { skinQuizResultColumns } from '@/features/analytics'

export function SkinQuizResultsPage() {
  return (
    <ResourcePage<SkinQuizResult>
      title="Teri testi natijalari"
      api={skinQuizResultApi}
      queryKey={['skin-quiz-results']}
      columns={skinQuizResultColumns}
    />
  )
}
