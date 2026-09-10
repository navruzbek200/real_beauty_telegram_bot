import { ResourcePage } from '@/widgets/resource-crud'
import { topProductApi, type TopProduct } from '@/entities/product'
import {
  topProductColumns,
  topProductFormConfig,
  toTopProductFormData,
  type TopProductFormValues,
} from '@/features/product'

export function TopProductsPage() {
  return (
    <ResourcePage<TopProduct, TopProductFormValues, FormData, FormData>
      title="Bu oydagi top mahsulotlar"
      api={topProductApi}
      queryKey={['top-products']}
      columns={topProductColumns}
      searchPlaceholder="Nomi bo'yicha qidirish..."
      permissions={{
        add: 'products.add_topproduct',
        change: 'products.change_topproduct',
        delete: 'products.delete_topproduct',
      }}
      formConfig={topProductFormConfig}
      toCreatePayload={toTopProductFormData}
      toUpdatePayload={toTopProductFormData}
      createLabel="+ Yangi qo'shish"
    />
  )
}
