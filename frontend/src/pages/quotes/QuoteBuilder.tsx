import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../../api/client'
import DemoBadge from '../../components/DemoBadge'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import Field from '../../components/ui/Field'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import type { ProductDoc } from '../../components/ProductForm'
import { INCOTERMS, PAYMENT_TERMS } from '../../data/incoterms'
import { numToInput, parseLocaleNumber } from '../../i18n/format'
import type { Lead } from '../leads/types'
import LogisticsPanel from './LogisticsPanel'
import type { Quote } from './types'

const plus30 = () => {
  const d = new Date(Date.now() + 30 * 864e5)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export default function QuoteBuilder() {
  const { t } = useTranslation()
  const { id = '' } = useParams()
  const [lead, setLead] = useState<Lead | null>(null)
  const [products, setProducts] = useState<ProductDoc[] | null>(null)
  const [pid, setPid] = useState('')
  const [qty, setQty] = useState('')
  const [price, setPrice] = useState('')
  const [cur, setCur] = useState('EUR')
  const [inc, setInc] = useState('DAP')
  const [pay, setPay] = useState('lc')
  const [until, setUntil] = useState(plus30())
  const [weight, setWeight] = useState('')
  const [needW, setNeedW] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [fieldErr, setFieldErr] = useState<Record<string, string>>({})
  const [quote, setQuote] = useState<Quote | null>(null)
  const product = products?.find((p) => p.id === pid)

  useEffect(() => {
    Promise.all([api<Lead>(`/api/leads/${id}`), api<ProductDoc[]>('/api/products')])
      .then(([l, ps]) => { setLead(l); setProducts(ps); if (ps[0]) setPid(ps[0].id) })
      .catch((x) => setErr(x instanceof ApiError ? t(x.messageKey) : t('errors.network')))
  }, [id, t])

  useEffect(() => {
    if (!pid) return
    api<{ unit_price: number; currency: string }>(`/api/quotes/suggest?product_id=${pid}`)
      .then((s) => { setPrice(numToInput(s.unit_price)); setCur(s.currency) }).catch(() => { /* price stays editable */ })
  }, [pid])

  async function submit(e: FormEvent) {
    e.preventDefault()
    const q = parseLocaleNumber(qty), p = parseLocaleNumber(price)
    const w = weight.trim() ? parseLocaleNumber(weight) : null
    const fe: Record<string, string> = {}
    if (q === null || q <= 0) fe.qty = t('errors.invalid_quantity')
    if (p === null || p <= 0) fe.price = t('errors.validation_error')
    if (weight.trim() && (w === null || w <= 0)) fe.weight = t('errors.validation_error')
    setFieldErr(fe); setErr(''); setQuote(null)
    if (Object.keys(fe).length || q === null || p === null) return
    setBusy(true)
    try {
      setQuote(await api<Quote>('/api/quotes', {
        method: 'POST',
        json: { lead_id: id, product_id: pid, quantity: q, unit_price: p, currency: cur, incoterm: inc, payment_terms: pay, valid_until: until, ...(w ? { unit_weight_kg: w } : {}) },
      }))
    } catch (x) {
      if (!(x instanceof ApiError)) setErr(t('errors.network'))
      else if (x.code === 'below_floor') setFieldErr({ price: t('quotes.belowFloor') })
      else if (x.code === 'needs_weight') { setNeedW(true); setFieldErr({ weight: t('quotes.errors.needs_weight') }) }
      else if (x.code === 'floor_currency_mismatch' || x.code === 'freight_currency_mismatch') setFieldErr({ currency: t(`quotes.errors.${x.code}`) })
      else setErr(t(x.messageKey))
    }
    setBusy(false)
  }

  if (!lead || !products) return <p role={err ? 'alert' : 'status'} className={err ? 'text-brand font-semibold' : ''}>{err || t('common.loading')}</p>
  if (products.length === 0) return <p role="status">{t('quotes.noProducts')}</p>

  return (
    <section className="space-y-4">
      <Link to={`/leads/${id}`} className="underline min-h-11 inline-flex items-center">← {t('leads.detail.back')}</Link>
      <Card className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-semibold">{t('quotes.title')}</h1>
          {lead.is_demo && <DemoBadge />}
        </div>
        <p className="text-sm"><span className="font-semibold">{t('quotes.for')}:</span> {lead.company_name} ({lead.country})</p>
        <form onSubmit={submit} noValidate className="grid sm:grid-cols-2 gap-4">
          <Field label={t('quotes.product')}><Select value={pid} onChange={(e) => setPid(e.target.value)}>{products.map((p) => <option key={p.id} value={p.id}>{p.name_tr}</option>)}</Select></Field>
          <Field label={t('quotes.quantity', { unit: product?.unit ?? '' })} error={fieldErr.qty}><Input inputMode="decimal" value={qty} onChange={(e) => setQty(e.target.value)} /></Field>
          <Field label={t('quotes.unitPrice')} error={fieldErr.price}><Input inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value)} /></Field>
          <Field label={t('quotes.currency')} error={fieldErr.currency}><Select value={cur} onChange={(e) => setCur(e.target.value)}><option>EUR</option><option>USD</option></Select></Field>
          <Field label={t('quotes.incoterm')} hint={t(`quotes.incoterms.${inc}`)}><Select value={inc} onChange={(e) => setInc(e.target.value)}>{INCOTERMS.map((i) => <option key={i} value={i}>{i}</option>)}</Select></Field>
          <Field label={t('quotes.payment')}><Select value={pay} onChange={(e) => setPay(e.target.value)}>{PAYMENT_TERMS.map((k) => <option key={k} value={k}>{t(`quotes.payments.${k}`)}</option>)}</Select></Field>
          <Field label={t('quotes.validUntil')}><Input type="date" value={until} onChange={(e) => setUntil(e.target.value)} /></Field>
          {(needW || product?.unit_weight_kg == null) && (
            <Field label={t('quotes.unitWeight')} hint={t('quotes.unitWeightHint')} error={fieldErr.weight}><Input inputMode="decimal" value={weight} onChange={(e) => setWeight(e.target.value)} /></Field>
          )}
          <div className="sm:col-span-2"><Button type="submit" disabled={busy}>{busy ? t('quotes.saving') : t('quotes.calculate')}</Button></div>
        </form>
        {err && <p role="alert" className="text-brand font-semibold">{err}</p>}
      </Card>

      {quote && (
        <Card className="space-y-3" aria-live="polite">
          <p role="status" className="font-semibold">{t('quotes.saved')}</p>
          <LogisticsPanel est={quote.logistics_estimate} included={quote.freight_included} total={quote.total} currency={quote.currency} />
          <p className="text-sm">{t('quotes.queueNote')}</p>
          <div className="flex flex-wrap gap-2">
            <a href={`/api/quotes/${quote.id}/pdf?preview=1`} target="_blank" rel="noreferrer" className="min-h-11 inline-flex items-center px-4 rounded-md font-semibold border border-slate-300 bg-white">{t('quotes.pdfPreview')}</a>
            <Link to="/approvals" className="min-h-11 inline-flex items-center px-4 rounded-md font-semibold bg-navy text-white">{t('quotes.goApprovals')}</Link>
          </div>
        </Card>
      )}
    </section>
  )
}
