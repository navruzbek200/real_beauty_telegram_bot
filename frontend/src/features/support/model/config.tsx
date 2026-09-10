import { z } from 'zod'

import type { ResourceColumn, ResourceFormConfig } from '@/shared/lib/resource-crud-types'
import { Badge } from '@/shared/ui'
import type { SupportAdmin, SupportThread } from '@/entities/support'

export const supportThreadColumns: ResourceColumn<SupportThread>[] = [
  { key: 'user_name', header: 'Foydalanuvchi', render: (t) => t.user_name },
  { key: 'subject', header: 'Mavzu', render: (t) => t.subject || '—' },
  {
    key: 'status',
    header: 'Holat',
    render: (t) => (
      <Badge tone={t.awaiting_reply ? 'danger' : t.status === 'closed' ? 'neutral' : 'success'}>
        {t.awaiting_reply ? 'Javob kutmoqda' : t.status === 'closed' ? 'Yopilgan' : 'Javob berildi'}
      </Badge>
    ),
  },
  {
    key: 'last_message_at',
    header: 'Oxirgi xabar',
    sortField: 'last_message_at',
    render: (t) => new Date(t.last_message_at as string).toLocaleString('uz-UZ'),
  },
]

export const supportAdminFormSchema = z.object({
  telegram_user_id: z.coerce.number().int().min(1),
  name: z.string().optional(),
  enabled: z.boolean(),
})
export type SupportAdminFormValues = z.infer<typeof supportAdminFormSchema>
export const supportAdminFormConfig: ResourceFormConfig<SupportAdminFormValues> = {
  schema: supportAdminFormSchema,
  fields: [
    { name: 'telegram_user_id', label: 'Telegram ID', type: 'number', help: 'Xodimning shaxsiy raqamli IDsi (@userinfobot ga yozsa chiqadi). Username emas!' },
    { name: 'name', label: 'Ism', type: 'text', help: 'Ixtiyoriy — birinchi javobidan keyin o\'zi to\'ladi.' },
    { name: 'enabled', label: 'Faol', type: 'checkbox', help: 'O\'chirilgan admin guruhda yozsa ham mijozga bormaydi.' },
  ],
  defaultValues: { telegram_user_id: 0, name: '', enabled: true },
  toFormValues: (item) => ({
    telegram_user_id: (item.telegram_user_id as number) ?? 0,
    name: (item.name as string) ?? '',
    enabled: Boolean(item.enabled),
  }),
}
export const supportAdminColumns: ResourceColumn<SupportAdmin>[] = [
  { key: 'name', header: 'Ism', render: (a) => a.name || a.telegram_user_id },
  { key: 'telegram_user_id', header: 'Telegram ID', render: (a) => a.telegram_user_id },
  {
    key: 'enabled',
    header: 'Holat',
    render: (a) => <Badge tone={a.enabled ? 'success' : 'neutral'}>{a.enabled ? 'Faol' : "O'chirilgan"}</Badge>,
  },
]

export const supportSettingsFormSchema = z.object({
  group_chat_id: z.coerce.number().optional(),
})
export type SupportSettingsFormValues = z.infer<typeof supportSettingsFormSchema>
export const supportSettingsFormConfig: ResourceFormConfig<SupportSettingsFormValues> = {
  schema: supportSettingsFormSchema,
  fields: [
    {
      name: 'group_chat_id',
      label: 'Guruh Chat ID',
      type: 'number',
      help: 'Botni guruhga qo\'shing, keyin guruhga @getidsbot ni qo\'shib IDni oling. '
        + 'Odatda minus bilan boshlanadi, masalan: -1001234567890. Saqlagach «Ulanishni tekshirish»ni bosing.',
    },
  ],
  defaultValues: { group_chat_id: undefined },
  toFormValues: (item) => ({ group_chat_id: (item.group_chat_id as number) ?? undefined }),
}
