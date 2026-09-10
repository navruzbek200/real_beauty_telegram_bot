import { z } from 'zod'

import type { ResourceColumn, ResourceFormConfig } from '@/shared/lib/resource-crud-types'
import { Badge } from '@/shared/ui'
import type {
  AutoMessage,
  Broadcast,
  MessageTemplate,
} from '@/entities/campaign'

// --- Message templates (edit-only, superuser) ---
export const messageTemplateFormSchema = z.object({
  name: z.string().min(1),
  body: z.string().min(1),
  is_active: z.boolean(),
})
export type MessageTemplateFormValues = z.infer<typeof messageTemplateFormSchema>
export const messageTemplateFormConfig: ResourceFormConfig<MessageTemplateFormValues> = {
  schema: messageTemplateFormSchema,
  fields: [
    { name: 'name', label: 'Nomi', type: 'text', help: 'Faqat admin uchun ko\'rinadi — mijozga yuborilmaydi.' },
    {
      name: 'body',
      label: 'Xabar matni',
      type: 'textarea',
      help: 'HTML ishlatsa bo\'ladi: <b>qalin</b>, <i>yotiq</i>. {{ user.full_name }} — mijoz ismi bilan almashadi. '
        + 'Masalan: «Salom, {{ user.full_name }}! Xush kelibsiz 🌸»',
    },
    { name: 'is_active', label: 'Faol', type: 'checkbox', help: 'O\'chirsangiz bot bu xabarni yubormaydi.' },
  ],
  defaultValues: { name: '', body: '', is_active: true },
  toFormValues: (item) => ({
    name: (item.name as string) ?? '',
    body: (item.body as string) ?? '',
    is_active: Boolean(item.is_active),
  }),
}
export const messageTemplateColumns: ResourceColumn<MessageTemplate>[] = [
  { key: 'name', header: 'Nomi', render: (t) => t.name },
  { key: 'type', header: 'Turi', render: (t) => t.template_type },
  {
    key: 'is_active',
    header: 'Holat',
    render: (t) => <Badge tone={t.is_active ? 'success' : 'neutral'}>{t.is_active ? 'Yoqilgan' : "O'chirilgan"}</Badge>,
  },
]

// --- Auto messages ---
export const autoMessageFormSchema = z.object({
  name: z.string().min(1),
  trigger: z.enum(['after_purchase', 'after_registration']),
  delay_value: z.coerce.number().int().min(1),
  delay_unit: z.enum(['minute', 'hour', 'day']),
  body: z.string().min(1),
  is_active: z.boolean(),
  is_test_mode: z.boolean(),
})
export type AutoMessageFormValues = z.infer<typeof autoMessageFormSchema>
export const autoMessageFormConfig: ResourceFormConfig<AutoMessageFormValues> = {
  schema: autoMessageFormSchema,
  fields: [
    { name: 'name', label: 'Nomi', type: 'text', help: 'Masalan: «Xariddan 7 kun keyin — natija so\'rash». Faqat admin ko\'radi.' },
    {
      name: 'trigger',
      label: 'Qachondan hisoblanadi',
      type: 'select',
      options: [
        { value: 'after_purchase', label: 'Xariddan keyin' },
        { value: 'after_registration', label: "Ro'yxatdan o'tgandan keyin" },
      ],
      help: 'Vaqt shu voqeadan boshlab sanaladi.',
    },
    { name: 'delay_value', label: 'Qancha vaqtdan keyin', type: 'number', help: 'Masalan: 7 (pastdagi birlik bilan birga o\'qiladi — «7 kun»).' },
    {
      name: 'delay_unit',
      label: 'Vaqt birligi',
      type: 'select',
      options: [
        { value: 'minute', label: 'daqiqa' },
        { value: 'hour', label: 'soat' },
        { value: 'day', label: 'kun' },
      ],
    },
    {
      name: 'body',
      label: 'Xabar matni',
      type: 'textarea',
      help: 'HTML mumkin: <b>qalin</b>, <i>yotiq</i>. {{ user.full_name }} — mijoz ismi, {{ product.name }} — mahsulot nomi. '
        + 'Masalan: «{{ user.full_name }}, {{ product.name }} natijasi qanday? 😊»',
    },
    { name: 'is_active', label: 'Yoqilgan', type: 'checkbox', help: 'O\'chiq bo\'lsa hech kimga yuborilmaydi.' },
    { name: 'is_test_mode', label: 'Sinov rejimi', type: 'checkbox', help: 'Yoqilsa xabar faqat sinov uchun belgilangan adminlarga boradi, mijozlarga emas.' },
  ],
  defaultValues: {
    name: '',
    trigger: 'after_purchase',
    delay_value: 7,
    delay_unit: 'day',
    body: '',
    is_active: true,
    is_test_mode: false,
  },
  toFormValues: (item) => ({
    name: (item.name as string) ?? '',
    trigger: (item.trigger as 'after_purchase' | 'after_registration') ?? 'after_purchase',
    delay_value: (item.delay_value as number) ?? 7,
    delay_unit: (item.delay_unit as 'minute' | 'hour' | 'day') ?? 'day',
    body: (item.body as string) ?? '',
    is_active: Boolean(item.is_active),
    is_test_mode: Boolean(item.is_test_mode),
  }),
}
export const autoMessageColumns: ResourceColumn<AutoMessage>[] = [
  { key: 'name', header: 'Nomi', render: (m) => m.name },
  { key: 'schedule', header: 'Qachon', render: (m) => m.schedule_label },
  {
    key: 'is_active',
    header: 'Holat',
    render: (m) => <Badge tone={m.is_active ? 'success' : 'neutral'}>{m.is_active ? 'Yoqilgan' : "O'chirilgan"}</Badge>,
  },
  { key: 'sent_total', header: 'Yuborilgan', render: (m) => `${m.sent_total ?? 0} ta` },
]

// --- Broadcasts ---
export const broadcastFormSchema = z.object({
  title: z.string().min(1),
  body: z.string().min(1),
  audience: z.enum(['all', 'by_skin', 'by_product']),
  skin_condition: z.string().optional(),
  product: z.coerce.number().optional(),
})
export type BroadcastFormValues = z.infer<typeof broadcastFormSchema>
export const broadcastFormConfig: ResourceFormConfig<BroadcastFormValues> = {
  schema: broadcastFormSchema,
  fields: [
    { name: 'title', label: 'Sarlavha', type: 'text', help: 'Masalan: «🌟 Bahoriy chegirmalar!». Faqat admin ro\'yxatida ko\'rinadi.' },
    {
      name: 'body',
      label: 'Xabar matni',
      type: 'textarea',
      help: 'Mijozga boradigan matn. HTML mumkin: <b>qalin</b>, <i>yotiq</i>. '
        + 'Masalan: «Bu hafta barcha serumlarga <b>-20%</b> 💸»',
    },
    {
      name: 'audience',
      label: 'Kimlarga yuborilsin',
      type: 'select',
      options: [
        { value: 'all', label: '📢 Barcha mijozlarga' },
        { value: 'by_skin', label: '🌿 Teri turi bo\'yicha' },
        { value: 'by_product', label: '🧴 Ma\'lum mahsulotni olganlarga' },
      ],
      help: 'Avval «Qoralama» saqlanadi — yuborish ro\'yxatdagi «Yuborish» tugmasi bilan.',
    },
    {
      name: 'skin_condition',
      label: 'Teri turi',
      type: 'select',
      options: [
        { value: 'dry', label: 'Quruq (dry)' },
        { value: 'oily', label: "Yog'li (oily)" },
        { value: 'combined', label: 'Aralash (combined)' },
        { value: 'normal', label: 'Normal' },
        { value: 'sensitive', label: 'Sezgir (sensitive)' },
      ],
      help: 'Faqat «Teri turi bo\'yicha» tanlanganda kerak. Boshqa holatda bo\'sh qoldiring.',
    },
    { name: 'product', label: 'Mahsulot ID si', type: 'number', help: 'Faqat «Mahsulotni olganlarga» uchun. ID ni «Mahsulotlar» sahifasidan ko\'ring.' },
  ],
  defaultValues: { title: '', body: '', audience: 'all', skin_condition: '', product: undefined },
  toFormValues: (item) => ({
    title: (item.title as string) ?? '',
    body: (item.body as string) ?? '',
    audience: (item.audience as 'all' | 'by_skin' | 'by_product') ?? 'all',
    skin_condition: (item.skin_condition as string) ?? '',
    product: (item.product as number) ?? undefined,
  }),
}
const BROADCAST_STATUS: Record<string, { tone: 'neutral' | 'success' | 'warning' | 'danger'; label: string }> = {
  draft: { tone: 'neutral', label: 'Qoralama — hali yuborilmagan' },
  sending: { tone: 'warning', label: 'Yuborilmoqda…' },
  sent: { tone: 'success', label: 'E\'lon yuborildi' },
  failed: { tone: 'danger', label: 'Xatolik' },
}

export const broadcastColumns: ResourceColumn<Broadcast>[] = [
  { key: 'title', header: 'Sarlavha', render: (b) => b.title },
  {
    key: 'audience',
    header: 'Kimlarga',
    render: (b) =>
      b.audience === 'all'
        ? 'Hamma'
        : b.audience === 'by_skin'
          ? 'Teri turi'
          : 'Mahsulot xaridorlari',
  },
  {
    key: 'status',
    header: 'Holat',
    render: (b) => {
      const s = BROADCAST_STATUS[b.status as string] ?? { tone: 'neutral' as const, label: b.status }
      return <Badge tone={s.tone}>{s.label}</Badge>
    },
  },
  {
    key: 'reach',
    header: 'Yetib bordi',
    render: (b) =>
      b.status === 'sent'
        ? `${b.sent_count}/${b.total} ta`
        : b.status === 'draft'
          ? `~${b.recipients_count ?? 0} ta kutilmoqda`
          : '—',
  },
  { key: 'created_at', header: 'Yaratilgan', render: (b) => new Date(b.created_at as string).toLocaleDateString('uz-UZ') },
]
