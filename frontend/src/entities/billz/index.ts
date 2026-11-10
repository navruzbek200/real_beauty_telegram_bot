import {apiClient} from '@/shared/api/client'
import type {Schemas} from '@/shared/api/schema'
import type {ListParams} from '@/shared/api/types'

export type BillzReceipt=Schemas['BillzReceipt']

export const billzReceiptApi={
  async list(params:ListParams){
    const {data,error}=await apiClient.GET('/api/v1/billz-receipts/',{params:{query:params}})
    if(error)throw error
    return data
  },
  async retrieve(id:number){
    const {data,error}=await apiClient.GET('/api/v1/billz-receipts/{id}/',{params:{path:{id}}})
    if(error)throw error
    return data
  },
  async preview(id:number,body?:string){
    const {data,error}=await apiClient.POST('/api/v1/billz-receipts/{id}/preview/',{params:{path:{id}},body:body===undefined?{}:{body}})
    if(error)throw error
    return data
  },
  async retry(id:number){
    const {data,error}=await apiClient.POST('/api/v1/billz-receipts/{id}/retry/',{params:{path:{id}}})
    if(error)throw error
    return data
  },
}
