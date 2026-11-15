import { useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import Field from '../../components/ui/Field'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import type { ProductDoc } from '../../components/ProductForm'
import { parseLocaleNumber } from '../../i18n/format'
import LogisticsPanel from '../quotes/LogisticsPanel'
import type { Estimate } from '../quotes/types'

interface Task { checklist: { key: string; done: boolean }[]; courier_estimate: Estimate }

export default function SampleTask({ lead, onClose }: { lead: string; onClose(): void }) {
  const { t } = useTranslation()
  const [products, setProducts] = useState<ProductDoc[]>([])
  const [pid, setPid] = useState('')
  const [w, setW] = useState('2')
  const [task, setTask] = useState<Task | null>(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    api<ProductDoc[]>('/api/products').then((ps) => { setProducts(ps); if (ps[0]) setPid(ps[0].id) }).catch(() => setErr(t('errors.network')))
  }, [t])

  async function go(e: FormEvent) {
    e.preventDefault(); setErr('')
    const kg = parseLocaleNumber(w)
    if (kg === null || kg <= 0 || kg > 30) return setErr(t('errors.validation_error'))
    setBusy(true)
    try { setTask(await api<Task>(`/api/leads/${lead}/sample-task`, { method: 'POST', json: { product_id: pid, sample_weight_kg: kg } })) }
    catch (x) { setErr(x instanceof ApiError ? t(x.messageKey) : t('errors.network')) }
    setBusy(false)
  }

  return (
    <Card className="space-y-3">
      <div className="flex items-start justify-between gap-2">
        <h2 className="text-lg font-semibold">{t('sample.title')}</h2>
        <Button variant="ghost" onClick={onClose}>{t('sample.close')}</Button>
      </div>
      <form onSubmit={go} noValidate className="grid sm:grid-cols-3 gap-3 items-end">
        <Field label={t('sample.product')}><Select value={pid} onChange={(e) => setPid(e.target.value)}>{products.map((p) => <option key={p.id} value={p.id}>{p.name_tr}</option>)}</Select></Field>
        <Field label={t('sample.weight')}><Input inputMode="decimal" value={w} onChange={(e) => setW(e.target.value)} /></Field>
        <Button type="submit" disabled={busy || !pid}>{t('sample.create')}</Button>
      </form>
      {err && <p role="alert" className="text-brand font-semibold">{err}</p>}
      {task && (
        <div className="space-y-3" aria-live="polite">
          <LogisticsPanel est={task.courier_estimate} />
          <h3 className="font-semibold">{t('sample.checklistTitle')}</h3>
          <ul className="space-y-1">
            {task.checklist.map((c) => (
              <li key={c.key} className="flex items-center gap-2"><input type="checkbox" checked={c.done} disabled aria-label={t(`sample.check.${c.key}`)} />{t(`sample.check.${c.key}`)}</li>
            ))}
          </ul>
          <p className="text-sm text-slate-700">{t('sample.note')}</p>
        </div>
      )}
    </Card>
  )
}
