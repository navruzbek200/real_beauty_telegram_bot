import { useState } from 'react'

import { ResourcePage } from '@/widgets/resource-crud'
import { Alert, Button, ConfirmDialog } from '@/shared/ui'
import { broadcastApi, type Broadcast } from '@/entities/campaign'
import { broadcastColumns, broadcastFormConfig, type BroadcastFormValues } from '@/features/campaign'

type Notice = { tone: 'success' | 'error'; text: string }

export function BroadcastsPage() {
  const [pendingId, setPendingId] = useState<number | null>(null)
  const [notice, setNotice] = useState<Notice>()
  const [confirming, setConfirming] = useState<Broadcast | null>(null)

  async function testToMe(item: Broadcast) {
    setPendingId(item.id)
    setNotice(undefined)
    try {
      const res = await broadcastApi.testToMe(item.id)
      setNotice({ tone: 'success', text: res.detail })
    } catch {
      setNotice({
        tone: 'error',
        text: "Test yuborilmadi. «Sozlamalar → Telegram guruh» da o'z Telegram ID ingizni tekshiring.",
      })
    } finally {
      setPendingId(null)
    }
  }

  async function sendNow() {
    if (!confirming) return
    setPendingId(confirming.id)
    setNotice(undefined)
    try {
      const res = await broadcastApi.sendNow(confirming.id)
      setNotice({ tone: 'success', text: res.detail })
    } catch {
      setNotice({ tone: 'error', text: 'Yuborishda xatolik.' })
    } finally {
      setPendingId(null)
      setConfirming(null)
    }
  }

  return (
    <div className="space-y-3">
      <Alert tone="info">
        E'lon yaratganingizdan keyin u <b>qoralama</b> bo'lib turadi. Mijozlarga borishi
        uchun ro'yxatdagi <b>«Yuborish»</b> tugmasini bosing. Avval «Menga test» bilan
        o'zingizga tekshirib ko'ring.
      </Alert>
      {notice && (
        <Alert tone={notice.tone} onDismiss={() => setNotice(undefined)}>
          {notice.text}
        </Alert>
      )}
      <ResourcePage<Broadcast, BroadcastFormValues, Partial<Broadcast>, Partial<Broadcast>>
        title="E'lonlar"
        api={broadcastApi}
        queryKey={['broadcasts']}
        columns={broadcastColumns}
        searchPlaceholder="Sarlavha yoki matn..."
        permissions={{ add: '*', change: '*', delete: '*' }}
        formConfig={broadcastFormConfig}
        toCreatePayload={(v) => v}
        toUpdatePayload={(v) => v}
        createLabel="+ Yangi e'lon"
        rowActions={(item) => (
          <>
            <Button
              variant="ghost"
              size="sm"
              loading={pendingId === item.id}
              onClick={() => testToMe(item)}
            >
              Menga test
            </Button>
            {(item.status === 'draft' || item.status === 'failed') && (
              <Button size="sm" disabled={pendingId === item.id} onClick={() => setConfirming(item)}>
                Yuborish
              </Button>
            )}
          </>
        )}
      />
      <ConfirmDialog
        open={confirming !== null}
        title="E'lonni yuborish"
        message={`"${confirming?.title}" barcha mos xaridorlarga yuboriladi. Bu amalni ortga qaytarib bo'lmaydi.`}
        confirmLabel="Ha, yuborish"
        pending={pendingId === confirming?.id}
        onConfirm={sendNow}
        onCancel={() => setConfirming(null)}
      />
    </div>
  )
}
