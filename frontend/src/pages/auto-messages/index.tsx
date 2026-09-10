import { useState } from 'react'

import { ResourcePage } from '@/widgets/resource-crud'
import { Alert, Button } from '@/shared/ui'
import { autoMessageApi, type AutoMessage } from '@/entities/campaign'
import { autoMessageColumns, autoMessageFormConfig, type AutoMessageFormValues } from '@/features/campaign'

type Notice = { tone: 'success' | 'error'; text: string }

export function AutoMessagesPage() {
  const [pendingId, setPendingId] = useState<number | null>(null)
  const [notice, setNotice] = useState<Notice>()

  async function testToMe(item: AutoMessage) {
    setPendingId(item.id)
    setNotice(undefined)
    try {
      const res = await autoMessageApi.testToMe(item.id)
      setNotice({ tone: 'success', text: res.detail })
    } catch {
      setNotice({ tone: 'error', text: 'Test yuborilmadi.' })
    } finally {
      setPendingId(null)
    }
  }

  return (
    <div className="space-y-3">
      {notice && (
        <Alert tone={notice.tone} onDismiss={() => setNotice(undefined)}>
          {notice.text}
        </Alert>
      )}
      <ResourcePage<AutoMessage, AutoMessageFormValues, AutoMessage, Partial<AutoMessage>>
        title="Avtomatik xabarlar"
        api={autoMessageApi}
        queryKey={['auto-messages']}
        columns={autoMessageColumns}
        searchPlaceholder="Nomi yoki matn..."
        permissions={{ add: '*', change: '*', delete: '*' }}
        formConfig={autoMessageFormConfig}
        toCreatePayload={(v) => v as AutoMessage}
        toUpdatePayload={(v) => v}
        rowActions={(item) => (
          <Button
            variant="ghost"
            size="sm"
            loading={pendingId === item.id}
            onClick={() => testToMe(item)}
          >
            Menga test
          </Button>
        )}
      />
    </div>
  )
}
