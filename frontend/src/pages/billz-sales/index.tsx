import {useRef,useState} from 'react'
import {useQuery,useQueryClient} from '@tanstack/react-query'

import {billzReceiptApi,type BillzReceipt} from '@/entities/billz'
import {messageTemplateApi,type MessageTemplate} from '@/entities/campaign'
import {useSessionStore} from '@/entities/session'
import {purchaseVariables} from '@/features/campaign'
import {ResourcePage} from '@/widgets/resource-crud'
import {Alert,Badge,Button,Dialog,Input,Label,Select,Spinner,Textarea} from '@/shared/ui'
import type {ResourceColumn} from '@/shared/lib/resource-crud-types'

type Notice={tone:'success'|'error';text:string}
function time(value:string|null|undefined){return value?new Date(value).toLocaleString('uz-UZ',{timeZone:'Asia/Tashkent'}):'—'}

function ReceiptBadge({receipt}:{receipt:BillzReceipt}){
  const state=receipt.notification_state
  const tone=state==='sent'?'success':state==='failed'||state==='unknown'?'danger':state==='pending'||state==='sending'?'warning':'neutral'
  return <Badge tone={tone}>{receipt.notification_label}</Badge>
}

const columns:ResourceColumn<BillzReceipt>[]=[
  {key:'receipt',header:'Chek',sortField:'purchased_at',render:r=><div><p className="font-medium">№{r.order_number||r.order_id.slice(0,8)}</p><p className="text-xs text-slate-400">{time(r.purchased_at)}</p>{r.shop_name&&<p className="text-xs text-slate-500">{r.shop_name}</p>}</div>},
  {key:'customer',header:'Mijoz',render:r=><div><p>{r.customer_name||'Ism kiritilmagan'}</p><p className="text-xs text-slate-500">{r.phone_number||'Telefon kiritilmagan'}</p></div>},
  {key:'products',header:'BILLZ’dagi mahsulotlar',render:r=><ul className="min-w-40 space-y-1">{r.products.map(p=><li key={p.id} className={p.cancelled?'text-slate-400 line-through':''}>{p.product_name} × {Number(p.quantity)}{Number(p.returned_quantity)>0&&<span className="text-xs text-slate-400"> · {Number(p.returned_quantity)} qaytarilgan</span>}</li>)}</ul>},
  {key:'message',header:'Telegram xabari',render:r=><div className="space-y-1"><ReceiptBadge receipt={r}/>{r.sent_at&&<p className="text-xs text-slate-400">{time(r.sent_at)}</p>}{r.last_error&&<p className="max-w-xs text-xs text-red-600">{r.last_error}</p>}</div>},
]

function ThanksEditor({template,sampleId}:{template:MessageTemplate;sampleId?:number}){
  const queryClient=useQueryClient()
  const [body,setBody]=useState(template.body)
  const [bodyRu,setBodyRu]=useState(template.body_ru??'')
  const [bodyEn,setBodyEn]=useState(template.body_en??'')
  const [enabled,setEnabled]=useState(template.is_active??true)
  const [pending,setPending]=useState(false)
  const [notice,setNotice]=useState<Notice>()
  const [preview,setPreview]=useState('')
  const input=useRef<HTMLTextAreaElement>(null)
  async function save(){
    setPending(true);setNotice(undefined)
    try{
      await messageTemplateApi.update(template.id,{body,body_ru:bodyRu,body_en:bodyEn,is_active:enabled})
      await queryClient.invalidateQueries({queryKey:['purchase-thanks-template']})
      await queryClient.invalidateQueries({queryKey:['billz-receipts']})
      setNotice({tone:'success',text:'Matn saqlandi. Keyingi yangi xaridlarga shu matn yuboriladi.'})
    }catch(error){
      const data=error as Record<string,unknown>
      setNotice({tone:'error',text:typeof data?.detail==='string'?data.detail:Object.values(data??{}).flat().join(' ')||'Matn saqlanmadi. O‘zgaruvchilarni tekshiring.'})
    }finally{setPending(false)}
  }
  async function showPreview(){
    if(!sampleId)return
    setPending(true)
    try{setPreview((await billzReceiptApi.preview(sampleId,body)).text)}catch{setNotice({tone:'error',text:'Namuna tayyorlanmadi. Matnni tekshiring.'})}finally{setPending(false)}
  }
  return <details open className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
    <summary className="cursor-pointer font-semibold">Xarid uchun minnatdorchilik matni</summary>
    <div className="mt-3 space-y-3">
      <p className="text-sm text-slate-500">Bir marta sozlang: yangi chek kelganda mijoz ismi va barcha mahsulotlar avtomatik qo‘yiladi. Video yoki katalogga qo‘lda biriktirish talab qilinmaydi.</p>
      {notice&&<Alert tone={notice.tone}>{notice.text}</Alert>}
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={enabled} onChange={e=>setEnabled(e.target.checked)}/>Yangi xaridlarga avtomatik rahmat xabari yuborilsin</label>
      <Label htmlFor="thanks-body">O‘zbekcha matn</Label>
      <Textarea id="thanks-body" ref={input} value={body} onChange={e=>setBody(e.target.value)} rows={9}/>
      <div className="flex flex-wrap gap-1">{purchaseVariables.map(variable=><Button key={variable.value} variant="ghost" size="sm" onClick={()=>{
        const start=input.current?.selectionStart??body.length,end=input.current?.selectionEnd??body.length
        setBody(body.slice(0,start)+variable.value+body.slice(end))
        requestAnimationFrame(()=>{input.current?.focus();input.current?.setSelectionRange(start+variable.value.length,start+variable.value.length)})
      }}>+ {variable.label}</Button>)}</div>
      <p className="text-xs text-slate-400">Ism yoki mahsulot o‘zgaruvchisini yozmasangiz ham bot ularni xabarga qo‘shadi. Matn o‘zgarishi avval yuborilgan xabarlarni takrorlamaydi.</p>
      <details><summary className="cursor-pointer text-sm text-slate-500">Ruscha va inglizcha matnlar</summary><div className="mt-2 space-y-2"><Label htmlFor="thanks-ru">Ruscha</Label><Textarea id="thanks-ru" value={bodyRu} onChange={e=>setBodyRu(e.target.value)} rows={5}/><Label htmlFor="thanks-en">Inglizcha</Label><Textarea id="thanks-en" value={bodyEn} onChange={e=>setBodyEn(e.target.value)} rows={5}/></div></details>
      <div className="flex flex-wrap gap-2"><Button loading={pending} onClick={save}>Matnni saqlash</Button><Button variant="secondary" disabled={!sampleId||pending} onClick={showPreview}>Chek bilan oldindan ko‘rish</Button></div>
      {preview&&<div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800"><p className="mb-2 text-xs text-slate-500">Faqat namuna. Mijozga yuborilmadi.</p><p className="whitespace-pre-wrap text-sm">{preview}</p></div>}
    </div>
  </details>
}

function ReceiptDialog({id,onClose}:{id:number;onClose:()=>void}){
  const detail=useQuery({queryKey:['billz-receipts','detail',id],queryFn:()=>billzReceiptApi.retrieve(id)})
  const preview=useQuery({queryKey:['billz-receipts','preview',id],queryFn:()=>billzReceiptApi.preview(id),enabled:!!detail.data&&!detail.data.message_text})
  const receipt=detail.data
  return <Dialog open title={`Chek №${receipt?.order_number??id}`} onClose={onClose}>
    {detail.isLoading?<Spinner/>:receipt?<div className="space-y-3"><p>{receipt.customer_name} · {receipt.phone_number}</p><ReceiptBadge receipt={receipt}/><p className="text-xs text-slate-500">{time(receipt.purchased_at)}</p>{receipt.last_error&&<Alert tone="error">{receipt.last_error}</Alert>}<h3 className="font-medium">{receipt.notification_state==='sent'?'Yuborilgan matn':receipt.message_text?'Tayyorlangan matn':'Joriy matn namunasi'}</h3><p className="whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm dark:bg-slate-800">{receipt.message_text||preview.data?.text||(preview.isError?'Namuna tayyorlanmadi.':'Tayyorlanmoqda…')}</p><p className="text-xs text-slate-400">“Yuborildi” — Telegram xabarni qabul qilgan. Bu mijoz o‘qiganini bildirmaydi.</p></div>:<Alert tone="error">Chekni yuklab bo‘lmadi.</Alert>}
  </Dialog>
}

export function BillzSalesPage(){
  const isAdmin=useSessionStore(s=>s.user?.is_superuser??false)
  const queryClient=useQueryClient()
  const [selected,setSelected]=useState<number|null>(null)
  const [notice,setNotice]=useState<Notice>()
  const [retrying,setRetrying]=useState<number|null>(null)
  const template=useQuery({queryKey:['purchase-thanks-template'],queryFn:async()=> (await messageTemplateApi.list({page_size:100})).results.find(item=>item.template_type==='purchase_thanks'),enabled:isAdmin})
  const sample=useQuery({queryKey:['billz-receipts','sample'],queryFn:()=>billzReceiptApi.list({page_size:1})})
  async function retry(receipt:BillzReceipt){
    setRetrying(receipt.id)
    try{const response=await billzReceiptApi.retry(receipt.id);setNotice({tone:'success',text:response.detail});await queryClient.invalidateQueries({queryKey:['billz-receipts']})}catch{setNotice({tone:'error',text:'Xabar qayta navbatga qo‘yilmadi. Sahifani yangilab holatini tekshiring.'})}finally{setRetrying(null)}
  }
  return <div className="space-y-4">
    <Alert tone="info">Do‘kondagi chek va mahsulotlar BILLZ’dan avtomatik keladi. Botga o‘z raqami bilan ulangan mijozga yangi chek uchun bitta minnatdorchilik xabari yuboriladi. Eski tarix va bekor qilingan savdolar ham shu yerda saqlanadi.</Alert>
    {isAdmin&&template.data&&<ThanksEditor key={template.data.id} template={template.data} sampleId={sample.data?.results[0]?.id}/>}
    {isAdmin&&template.isError&&<Alert tone="error">Xabar matnini yuklab bo‘lmadi. Sahifani yangilang.</Alert>}
    {notice&&<Alert tone={notice.tone} onDismiss={()=>setNotice(undefined)}>{notice.text}</Alert>}
    <ResourcePage<BillzReceipt> title="BILLZ savdolari" api={billzReceiptApi} queryKey={['billz-receipts']} columns={columns} filterKeys={['notification_state','date_from','date_to']} searchPlaceholder="Mijoz, telefon, chek yoki mahsulot…"
      filterBar={state=><><Select aria-label="Xabar holati" className="max-w-56" value={state.filters.notification_state??''} onChange={e=>state.setFilter('notification_state',e.target.value||null)}>{[['','Barcha holatlar'],['sent','Yuborildi'],['pending','Navbatda'],['unlinked','Telegramga ulanmagan'],['unverified','Telefon tasdig‘i kerak'],['failed','Yuborilmadi'],['unknown','Yetkazilishi noaniq'],['historical','Eski xaridlar'],['cancelled','Bekor/qaytarilgan']].map(([value,label])=><option key={value} value={value}>{label}</option>)}</Select><Input aria-label="Boshlanish sanasi" type="date" className="max-w-44" value={state.filters.date_from??''} onChange={e=>state.setFilter('date_from',e.target.value||null)}/><Input aria-label="Tugash sanasi" type="date" className="max-w-44" value={state.filters.date_to??''} onChange={e=>state.setFilter('date_to',e.target.value||null)}/><Button variant="ghost" onClick={()=>queryClient.invalidateQueries({queryKey:['billz-receipts']})}>Yangilash</Button></>}
      rowActions={receipt=><><Button variant="ghost" size="sm" onClick={()=>setSelected(receipt.id)}>Ko‘rish</Button>{isAdmin&&receipt.notification_state==='failed'&&<Button variant="secondary" size="sm" loading={retrying===receipt.id} onClick={()=>retry(receipt)}>Qayta urinish</Button>}</>}/>
    {selected!==null&&<ReceiptDialog id={selected} onClose={()=>setSelected(null)}/>}
  </div>
}
