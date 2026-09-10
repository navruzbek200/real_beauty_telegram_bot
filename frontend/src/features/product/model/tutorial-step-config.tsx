import { z } from 'zod'

import type { ResourceColumn, ResourceFormConfig, ResourceFormField } from '@/shared/lib/resource-crud-types'
import { Badge } from '@/shared/ui'
import type { ProductTutorialStep } from '@/entities/product'

export const tutorialStepFormSchema = z.object({
  product: z.coerce.number().min(1, 'Mahsulotni tanlang'),
  order: z.coerce.number().int().min(1),
  button_label: z.string().min(1, 'Tugma matni shart'),
  intro_text: z.string().optional(),
  video_file: z.instanceof(File).optional(),
})
export type TutorialStepFormValues = z.infer<typeof tutorialStepFormSchema>

/**
 * The product dropdown's options depend on the current catalogue, so the
 * form config is built per-render (see TutorialStepsPage) rather than
 * exported as a static constant like the other resource configs.
 */
export function buildTutorialStepFormConfig(
  productOptions: { value: string; label: string }[],
): ResourceFormConfig<TutorialStepFormValues> {
  const fields: ResourceFormField[] = [
    { name: 'product', label: 'Mahsulot', type: 'select', options: productOptions, help: 'Bu dars qaysi mahsulotga tegishli — mijoz botda va Mini Appda shu mahsulot ostida ko\'radi.' },
    {
      name: 'order',
      label: 'Ketma-ketlik',
      type: 'number',
      help: 'Tugmalar tartibi: 1, 2, 3 ... (kichik raqam yuqorida turadi).',
    },
    {
      name: 'button_label',
      label: 'Tugma matni',
      type: 'text',
      help: 'Botda ko\'rinadigan tugma, masalan: «1-qadam: Tozalash».',
    },
    {
      name: 'intro_text',
      label: 'Video oldidan matn (ixtiyoriy)',
      type: 'textarea',
      help: 'Ixtiyoriy. Bo\'sh qoldirsangiz — faqat video yuboriladi.',
    },
    {
      name: 'video_file',
      label: 'Video',
      type: 'file',
      help: 'Yuklamasangiz bot «tez orada» deb yozadi. Bot bu videoni har doim '
        + 'himoyalangan holda yuboradi — yuklab olish va forward qilish taqiqlangan.',
    },
  ]

  return {
    schema: tutorialStepFormSchema,
    fields,
    defaultValues: { product: 0, order: 1, button_label: '', intro_text: '' },
    toFormValues: (item) => ({
      product: (item.product as number) ?? 0,
      order: (item.order as number) ?? 1,
      button_label: (item.button_label as string) ?? '',
      intro_text: (item.intro_text as string) ?? '',
    }),
  }
}

export function toTutorialStepFormData(values: TutorialStepFormValues): FormData {
  const formData = new FormData()
  formData.set('product', String(values.product))
  formData.set('order', String(values.order))
  formData.set('button_label', values.button_label)
  formData.set('intro_text', values.intro_text ?? '')
  if (values.video_file) formData.set('video_file', values.video_file)
  return formData
}

export function tutorialStepColumns(
  productNameById: Map<number, string>,
): ResourceColumn<ProductTutorialStep>[] {
  return [
    {
      key: 'product',
      header: 'Mahsulot',
      render: (s) => productNameById.get(s.product) ?? `#${s.product}`,
    },
    { key: 'order', header: "Tartib", sortField: 'order', render: (s) => s.order },
    { key: 'button_label', header: 'Tugma matni', render: (s) => s.button_label },
    {
      key: 'has_video',
      header: 'Video',
      render: (s) => (
        <Badge tone={s.has_video ? 'success' : 'warning'}>
          {s.has_video ? 'Yuklangan' : "Yo'q"}
        </Badge>
      ),
    },
    {
      key: 'protect_content',
      header: 'Himoya',
      render: () => <Badge tone="success">Har doim yoqilgan</Badge>,
    },
  ]
}
