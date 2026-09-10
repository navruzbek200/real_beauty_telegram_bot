import { ResourcePage } from '@/widgets/resource-crud'
import { messageTemplateApi, type MessageTemplate } from '@/entities/campaign'
import {
  messageTemplateColumns,
  messageTemplateFormConfig,
  type MessageTemplateFormValues,
} from '@/features/campaign'

export function MessageTemplatesPage() {
  return (
    <ResourcePage<MessageTemplate, MessageTemplateFormValues, never, Partial<MessageTemplate>>
      title="Xabar shablonlari"
      api={messageTemplateApi}
      queryKey={['message-templates']}
      columns={messageTemplateColumns}
      searchPlaceholder="Nomi yoki matn..."
      permissions={{ change: '*' }}
      formConfig={messageTemplateFormConfig}
      toUpdatePayload={(v) => v}
    />
  )
}
