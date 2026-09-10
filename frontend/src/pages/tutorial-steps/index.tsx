import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'

import { ResourcePage } from '@/widgets/resource-crud'
import { Spinner } from '@/shared/ui'
import { productApi, tutorialStepApi, type ProductTutorialStep } from '@/entities/product'
import {
  buildTutorialStepFormConfig,
  toTutorialStepFormData,
  tutorialStepColumns,
  type TutorialStepFormValues,
} from '@/features/product'

export function TutorialStepsPage() {
  // The product dropdown needs the live catalogue, not a static enum — so
  // this page fetches it once and hands the options down to the form config.
  const productsQuery = useQuery({
    queryKey: ['products', 'all-for-select'],
    queryFn: () => productApi.list({ page_size: 200, ordering: 'name' }),
  })

  const products = useMemo(() => productsQuery.data?.results ?? [], [productsQuery.data])
  const productOptions = useMemo(
    () => products.map((p) => ({ value: String(p.id), label: p.name })),
    [products],
  )
  const productNameById = useMemo(
    () => new Map(products.map((p) => [p.id, p.name])),
    [products],
  )
  const formConfig = useMemo(
    () => buildTutorialStepFormConfig(productOptions),
    [productOptions],
  )
  const columns = useMemo(() => tutorialStepColumns(productNameById), [productNameById])

  if (productsQuery.isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    )
  }

  return (
    <ResourcePage<ProductTutorialStep, TutorialStepFormValues, FormData, FormData>
      title="Video darsliklar"
      api={tutorialStepApi}
      queryKey={['tutorial-steps']}
      columns={columns}
      searchPlaceholder="Tugma matni bo'yicha qidirish..."
      permissions={{
        add: 'products.add_producttutorialstep',
        change: 'products.change_producttutorialstep',
        delete: 'products.delete_producttutorialstep',
      }}
      formConfig={formConfig}
      toCreatePayload={toTutorialStepFormData}
      toUpdatePayload={toTutorialStepFormData}
      createLabel="+ Video qo'shish"
    />
  )
}
