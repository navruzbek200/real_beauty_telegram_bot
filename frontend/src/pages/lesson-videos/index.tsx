import { ResourcePage } from '@/widgets/resource-crud'
import { lessonVideoApi, type LessonVideo } from '@/entities/lesson'
import {
  lessonVideoColumns,
  lessonVideoFormConfig,
  toLessonVideoFormData,
  type LessonVideoFormValues,
} from '@/features/lesson'

export function LessonVideosPage() {
  return (
    <ResourcePage<LessonVideo, LessonVideoFormValues, FormData, FormData>
      title="Video darslar"
      api={lessonVideoApi}
      queryKey={['lesson-videos']}
      columns={lessonVideoColumns}
      searchPlaceholder="Dars nomi bo'yicha qidirish..."
      permissions={{
        add: 'lessons.add_lessonvideo',
        change: 'lessons.change_lessonvideo',
        delete: 'lessons.delete_lessonvideo',
      }}
      formConfig={lessonVideoFormConfig}
      toCreatePayload={toLessonVideoFormData}
      toUpdatePayload={toLessonVideoFormData}
      createLabel="+ Dars qo'shish"
    />
  )
}
