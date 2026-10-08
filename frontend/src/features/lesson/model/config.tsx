import { z } from 'zod'

import type { ResourceColumn, ResourceFormConfig } from '@/shared/lib/resource-crud-types'
import { Badge, CopyableCode } from '@/shared/ui'
import type { AccessCode, LessonUnlock, LessonVideo } from '@/entities/lesson'

/* ------------------------------------------------------------------ videos */

export const lessonVideoFormSchema = z.object({
  title: z.string().min(1, 'Nomi shart'),
  description: z.string().optional(),
  order: z.coerce.number().int().min(1),
  is_active: z.boolean(),
  video_file: z.instanceof(File).optional(),
  poster: z.instanceof(File).optional(),
  video_file_id: z.string().optional(),
})
export type LessonVideoFormValues = z.infer<typeof lessonVideoFormSchema>

export const lessonVideoFormConfig: ResourceFormConfig<LessonVideoFormValues> = {
  schema: lessonVideoFormSchema,
  fields: [
    {
      name: 'title',
      label: 'Nomi',
      type: 'text',
      help: "Mijoz «Darslar» bo'limida shu sarlavhani ko'radi.",
    },
    {
      name: 'description',
      label: 'Qisqa izoh',
      type: 'textarea',
      help: 'Ixtiyoriy. Ro‘yxatda sarlavha ostida ko‘rinadi.',
    },
    {
      name: 'order',
      label: 'Tartib',
      type: 'number',
      help: 'Kichik raqam yuqorida turadi: 1, 2, 3 …',
    },
    {
      name: 'video_file',
      label: 'Video fayl',
      type: 'file',
      help: 'MP4, eng ko‘pi 50 MB — Telegram bundan kattasini qabul qilmaydi. '
        + 'Bot bu videoni har doim himoyalangan yuboradi: forward, saqlash va '
        + 'nusxa olish taqiqlanadi.',
    },
    {
      name: 'poster',
      label: 'Muqova rasmi (ixtiyoriy)',
      type: 'file',
      help: 'Bo‘sh qoldirsangiz videodan avtomatik olinadi. Yoqmasa shu yerdan '
        + 'o‘z rasmingizni yuklang — vertikal (9:16) bo‘lgani chiroyliroq chiqadi.',
    },
    {
      name: 'video_file_id',
      label: 'Telegram video ID (ixtiyoriy)',
      type: 'text',
      help: 'Birinchi yuborilgandan keyin bot o‘zi to‘ldiradi. Boshqa botdan '
        + 'ko‘chirayotgan bo‘lsangiz qo‘lda ham kiritsangiz bo‘ladi.',
    },
    {
      name: 'is_active',
      label: 'Faol',
      type: 'checkbox',
      help: 'Belgi olib tashlansa dars mijozlarga ko‘rinmaydi.',
    },
  ],
  defaultValues: { title: '', description: '', order: 1, is_active: true, video_file_id: '' },
  toFormValues: (item) => ({
    title: (item.title as string) ?? '',
    description: (item.description as string) ?? '',
    order: (item.order as number) ?? 1,
    is_active: (item.is_active as boolean) ?? true,
    video_file_id: (item.video_file_id as string) ?? '',
  }),
}

export function toLessonVideoFormData(values: LessonVideoFormValues): FormData {
  const formData = new FormData()
  formData.set('title', values.title)
  formData.set('description', values.description ?? '')
  formData.set('order', String(values.order))
  formData.set('is_active', String(values.is_active))
  formData.set('video_file_id', values.video_file_id ?? '')
  if (values.video_file) formData.set('video_file', values.video_file)
  if (values.poster) formData.set('poster', values.poster)
  return formData
}

function clock(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

export const lessonVideoColumns: ResourceColumn<LessonVideo>[] = [
  { key: 'order', header: 'Tartib', sortField: 'order', render: (v) => v.order },
  {
    key: 'poster',
    header: '',
    render: (v) =>
      v.poster ? (
        <img
          src={v.poster}
          alt=""
          className="h-16 w-9 rounded-md border border-slate-200 object-cover dark:border-slate-700"
        />
      ) : (
        <div className="flex h-16 w-9 items-center justify-center rounded-md bg-slate-100 text-xs text-slate-300 dark:bg-slate-800">
          —
        </div>
      ),
  },
  { key: 'title', header: 'Nomi', sortField: 'title', render: (v) => v.title },
  {
    key: 'duration',
    header: 'Davomiyligi',
    render: (v) => (v.duration_seconds ? clock(v.duration_seconds) : '—'),
  },
  {
    key: 'video',
    header: 'Video',
    // Three states, not two: a cached Telegram id means the next customer gets
    // it instantly, an uploaded file means the first send still has to upload.
    render: (v) =>
      v.video_file_id ? (
        <Badge tone="success">Telegramda tayyor</Badge>
      ) : v.has_video ? (
        <Badge tone="info">Yuklangan</Badge>
      ) : (
        <Badge tone="danger">Video yo‘q</Badge>
      ),
  },
  {
    key: 'is_active',
    header: 'Holat',
    render: (v) => (
      <Badge tone={v.is_active ? 'success' : 'neutral'}>
        {v.is_active ? 'Faol' : 'Yashirilgan'}
      </Badge>
    ),
  },
]

/* ------------------------------------------------------------------- codes */

const STATE_LABEL: Record<string, { tone: 'success' | 'neutral' | 'danger'; text: string }> = {
  free: { tone: 'success', text: '🟢 Berish mumkin' },
  used: { tone: 'neutral', text: '✔️ Ishlatilgan' },
  expired: { tone: 'danger', text: 'Muddati tugagan' },
  off: { tone: 'neutral', text: 'O‘chirilgan' },
}

export const accessCodeColumns: ResourceColumn<AccessCode>[] = [
  {
    key: 'code',
    header: 'Kalit so‘z',
    sortField: 'code',
    render: (c) => <CopyableCode value={c.code} />,
  },
  {
    key: 'state',
    header: 'Holati',
    render: (c) => {
      const s = STATE_LABEL[c.state as string] ?? STATE_LABEL.off
      return <Badge tone={s.tone}>{s.text}</Badge>
    },
  },
  { key: 'redeemed_by', header: 'Kim ishlatgan', render: (c) => c.redeemed_by || '—' },
  {
    key: 'uses',
    header: 'Ishlatilgan',
    render: (c) => `${c.uses_count} / ${c.max_uses || '∞'}`,
  },
  { key: 'label', header: 'Izoh', render: (c) => c.label || '—' },
  {
    key: 'created_at',
    header: 'Yaratilgan',
    sortField: 'created_at',
    render: (c) => new Date(c.created_at as string).toLocaleDateString('uz-UZ'),
  },
]

export const accessCodeFormSchema = z.object({
  code: z.string().optional(),
  label: z.string().optional(),
  max_uses: z.coerce.number().int().min(0),
  is_active: z.boolean(),
})
export type AccessCodeFormValues = z.infer<typeof accessCodeFormSchema>

export const accessCodeFormConfig: ResourceFormConfig<AccessCodeFormValues> = {
  schema: accessCodeFormSchema,
  fields: [
    {
      name: 'code',
      label: 'Kalit so‘z',
      type: 'text',
      help: 'Bo‘sh qoldirsangiz tizim o‘zi tasodifiy kod yaratadi. '
        + 'Katta-kichik harf va tirelar ahamiyatsiz.',
    },
    {
      name: 'label',
      label: 'Izoh',
      type: 'text',
      help: 'O‘zingiz uchun: bu kalit kimga yoki nima uchun berilgani.',
    },
    {
      name: 'max_uses',
      label: 'Nechta mijozga',
      type: 'number',
      help: '1 — faqat bitta mijoz ishlatadi (tavsiya etiladi). 0 — cheksiz.',
    },
    { name: 'is_active', label: 'Faol', type: 'checkbox' },
  ],
  defaultValues: { code: '', label: '', max_uses: 1, is_active: true },
  toFormValues: (item) => ({
    code: (item.code as string) ?? '',
    label: (item.label as string) ?? '',
    max_uses: (item.max_uses as number) ?? 1,
    is_active: (item.is_active as boolean) ?? true,
  }),
}

export function toAccessCodePayload(values: AccessCodeFormValues): Record<string, unknown> {
  return {
    code: values.code ?? '',
    label: values.label ?? '',
    max_uses: values.max_uses,
    is_active: values.is_active,
  }
}

/* ----------------------------------------------------------------- unlocks */

export const lessonUnlockColumns: ResourceColumn<LessonUnlock>[] = [
  { key: 'user', header: 'Xaridor', render: (u) => u.user_name },
  {
    key: 'code',
    header: 'Ishlatilgan kalit',
    render: (u) =>
      u.code_value ? (
        <span className="font-mono text-sm tracking-wider">{u.code_value}</span>
      ) : (
        <Badge tone="info">Qo‘lda berilgan</Badge>
      ),
  },
  {
    key: 'unlocked_at',
    header: 'Ochilgan',
    sortField: 'unlocked_at',
    render: (u) => new Date(u.unlocked_at as string).toLocaleString('uz-UZ'),
  },
]

export const lessonUnlockFormSchema = z.object({
  user: z.coerce.number().min(1, 'Xaridorni tanlang'),
})
export type LessonUnlockFormValues = z.infer<typeof lessonUnlockFormSchema>

export function buildLessonUnlockFormConfig(
  customerOptions: { value: string; label: string }[],
): ResourceFormConfig<LessonUnlockFormValues> {
  return {
    schema: lessonUnlockFormSchema,
    fields: [
      {
        name: 'user',
        label: 'Xaridor',
        type: 'select',
        options: customerOptions,
        help: 'Tanlangan xaridorga darslar kalit so‘zsiz ochiladi. Mijoz '
          + 'Telegramini o‘chirib qayta ro‘yxatdan o‘tgan bo‘lsa yoki kalitini '
          + 'yo‘qotgan bo‘lsa shu yerdan bering.',
      },
    ],
    defaultValues: { user: 0 },
    toFormValues: (item) => ({ user: (item.user as number) ?? 0 }),
  }
}

export function toLessonUnlockPayload(values: LessonUnlockFormValues): Record<string, unknown> {
  return { user: values.user }
}
