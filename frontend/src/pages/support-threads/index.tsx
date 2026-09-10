import { useState } from 'react'

import { ResourcePage } from '@/widgets/resource-crud'
import { Alert, Badge, Button, Dialog, EmptyState, Select, Spinner } from '@/shared/ui'
import { supportThreadApi, type SupportThread } from '@/entities/support'
import { supportThreadColumns } from '@/features/support'
import { useQuery } from '@tanstack/react-query'

function ConversationDialog({ threadId, onClose }: { threadId: number | null; onClose: () => void }) {
  const query = useQuery({
    queryKey: ['support-threads', 'detail', threadId],
    queryFn: () => supportThreadApi.retrieve(threadId as number),
    enabled: threadId !== null,
  })
  const thread = query.data
  const messages = thread?.messages ?? []

  return (
    <Dialog
      open={threadId !== null}
      title={thread ? thread.user_name : 'Yozishmalar'}
      description={thread?.subject || undefined}
      onClose={onClose}
      widthClassName="max-w-2xl"
    >
      {query.isLoading ? (
        <div className="flex justify-center py-10">
          <Spinner className="h-8 w-8" />
        </div>
      ) : (
        <div className="space-y-4">
          <Alert tone="info">
            Mijozga javob berish uchun ulangan Telegram guruhida ushbu murojaatga
            <b> reply (javob)</b> qiling — javob botga o'zi yetkaziladi.
          </Alert>
          {messages.length === 0 ? (
            <EmptyState message="Xabarlar yo'q." />
          ) : (
            <div className="space-y-2">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`max-w-[80%] rounded-2xl px-3.5 py-2 text-sm ${
                    msg.direction === 'in'
                      ? 'bg-slate-100 dark:bg-slate-800'
                      : 'ml-auto bg-brand-50 dark:bg-brand-900/30'
                  }`}
                >
                  <div className="mb-1 flex items-center gap-2 text-xs text-slate-400">
                    <span className="font-medium">
                      {msg.direction === 'in' ? 'Mijoz' : "Do'kon"}
                    </span>
                    <span>{new Date(msg.created_at).toLocaleString('uz-UZ')}</span>
                  </div>
                  {msg.text || '📎 fayl'}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </Dialog>
  )
}

export function SupportThreadsPage() {
  const [viewing, setViewing] = useState<number | null>(null)

  return (
    <>
      <ResourcePage<SupportThread>
        title="Murojaatlar"
        api={supportThreadApi}
        queryKey={['support-threads']}
        columns={supportThreadColumns}
        filterKeys={['status', 'awaiting_reply']}
        searchPlaceholder="Foydalanuvchi yoki mavzu..."
        permissions={{ delete: '*' }}
        filterBar={(state) => (
          <>
            <Select
              value={state.filters.awaiting_reply ?? ''}
              onChange={(e) => state.setFilter('awaiting_reply', e.target.value || null)}
              className="max-w-48"
            >
              <option value="">Barcha murojaatlar</option>
              <option value="true">Javob kutayotganlar</option>
              <option value="false">Javob berilganlar</option>
            </Select>
            <Select
              value={state.filters.status ?? ''}
              onChange={(e) => state.setFilter('status', e.target.value || null)}
              className="max-w-40"
            >
              <option value="">Barcha holatlar</option>
              <option value="open">Ochiq</option>
              <option value="closed">Yopilgan</option>
            </Select>
          </>
        )}
        rowActions={(thread) => (
          <>
            {thread.awaiting_reply && (
              <span className="hidden sm:inline">
                <Badge tone="danger">Javob kutmoqda</Badge>
              </span>
            )}
            <Button variant="ghost" size="sm" onClick={() => setViewing(thread.id)}>
              Ko'rish
            </Button>
          </>
        )}
      />
      <ConversationDialog threadId={viewing} onClose={() => setViewing(null)} />
    </>
  )
}
