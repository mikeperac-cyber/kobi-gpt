import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../../api/client'
import { serverErrs, translateErrs } from '../../components/CompanyFields'
import ProductForm, { emptyProduct, productFromDoc, productPayload, type ProductDoc, type ProductDraft } from '../../components/ProductForm'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import Modal from '../../components/ui/Modal'
import Skeleton from '../../components/ui/Skeleton'
import { formatMoney, formatNumber } from '../../i18n/format'

export default function ProductsPage() {
  const { t } = useTranslation()
  const [items, setItems] = useState<ProductDoc[] | null>(null)
  const [top, setTop] = useState('')
  const [editing, setEditing] = useState<{ id: string | null; draft: ProductDraft } | null>(null)
  const [deleting, setDeleting] = useState<ProductDoc | null>(null)
  const [errs, setErrs] = useState<Record<string, string>>({})
  const [formTop, setFormTop] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => api<ProductDoc[]>('/api/products').then(setItems).catch((x) => setTop(serverErrs(x).top)), [])
  useEffect(() => { void load() }, [load])

  const open = (p?: ProductDoc) => { setErrs({}); setFormTop(''); setEditing({ id: p?.id ?? null, draft: p ? productFromDoc(p) : emptyProduct }) }
  const save = async (e: FormEvent) => {
    e.preventDefault()
    if (!editing) return
    const { payload, errs: ve } = productPayload(editing.draft, 'edit')
    setErrs(ve)
    setFormTop('')
    if (Object.keys(ve).length) return
    setBusy(true)
    try {
      await api(editing.id ? `/api/products/${editing.id}` : '/api/products', { method: editing.id ? 'PUT' : 'POST', json: payload })
      setEditing(null)
      await load()
    } catch (x) {
      const s = serverErrs(x)
      setErrs(s.fields)
      setFormTop(s.top)
    } finally {
      setBusy(false)
    }
  }
  const remove = async () => {
    if (!deleting) return
    setBusy(true)
    try {
      await api(`/api/products/${deleting.id}`, { method: 'DELETE' })
      setDeleting(null)
      await load()
    } catch (x) {
      setTop(serverErrs(x).top)
      setDeleting(null)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section>
      <div className="flex items-center justify-between gap-3 mb-4">
        <h1 className="text-2xl font-semibold">{t('products.pageTitle')}</h1>
        <Button onClick={() => open()}>{t('products.add')}</Button>
      </div>
      {top && <p role="alert" className="text-brand font-semibold mb-3">{t(top)}</p>}
      {!items && !top && <div role="status" aria-label={t('common.loading')}><Skeleton className="h-28" /></div>}
      {items?.length === 0 && <Card className="space-y-3"><p>{t('products.empty')}</p><Button onClick={() => open()}>{t('products.add')}</Button></Card>}
      <ul className="space-y-3">
        {items?.map((p) => (
          <li key={p.id}>
            <Card className="flex gap-4">
              {p.photos[0]
                ? <img src={p.photos[0]} alt="" className="size-20 sm:size-24 rounded object-cover shrink-0" />
                : <div aria-hidden className="size-20 sm:size-24 rounded bg-slate-200 shrink-0" />}
              <div className="min-w-0 flex-1">
                <h2 className="font-semibold break-words">{p.name_tr}</h2>
                <p className="text-sm text-slate-600">{t('products.moqLine', { moq: formatNumber(p.moq), unit: t(`products.units.${p.unit}`) })}</p>
                <p className="text-sm text-slate-600">{t('products.floorLine', { price: formatMoney(p.price_floor, 'EUR') })}</p>
                <div className="flex gap-2 mt-2">
                  <Button variant="secondary" onClick={() => open(p)}>{t('products.edit')}</Button>
                  <Button variant="ghost" onClick={() => setDeleting(p)}>{t('products.delete')}</Button>
                </div>
              </div>
            </Card>
          </li>
        ))}
      </ul>
      {editing && (
        <Modal title={editing.id ? t('products.editTitle') : t('products.addTitle')} onClose={() => setEditing(null)}>
          <form onSubmit={save} noValidate className="space-y-4">
            <ProductForm mode="edit" value={editing.draft} onChange={(draft) => setEditing((e) => e && { ...e, draft })} errs={translateErrs(t, errs)} />
            {formTop && <p role="alert" className="text-brand font-semibold">{t(formTop)}</p>}
            <div className="flex gap-3">
              <Button type="button" variant="secondary" onClick={() => setEditing(null)}>{t('common.cancel')}</Button>
              <Button type="submit" disabled={busy} className="flex-1">{busy ? t('auth.submitting') : t('common.save')}</Button>
            </div>
          </form>
        </Modal>
      )}
      {deleting && (
        <Modal title={t('products.deleteTitle')} onClose={() => setDeleting(null)}>
          <p className="mb-4">{t('products.deleteBody', { name: deleting.name_tr })}</p>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={() => setDeleting(null)}>{t('common.cancel')}</Button>
            <Button className="flex-1" disabled={busy} onClick={() => void remove()}>{t('products.delete')}</Button>
          </div>
        </Modal>
      )}
    </section>
  )
}
