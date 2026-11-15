import { useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import Field from '../../components/ui/Field'
import Input from '../../components/ui/Input'
import { numToInput, parseLocaleNumber } from '../../i18n/format'

interface Rates {
  packaging_pct: number; ltl_bands: { max_kg: number; eur_per_kg: number }[]
  ftl_eur_per_truck: number; ftl_truck_capacity_kg: number; courier_eur_per_kg: number; courier_min_eur: number
}
type Form = { pack: string; bands: { max: string; rate: string }[]; ftl: string; cap: string; ckg: string; cmin: string }

const toForm = (r: Rates): Form => ({
  pack: numToInput(r.packaging_pct), bands: r.ltl_bands.map((b) => ({ max: numToInput(b.max_kg), rate: numToInput(b.eur_per_kg) })),
  ftl: numToInput(r.ftl_eur_per_truck), cap: numToInput(r.ftl_truck_capacity_kg), ckg: numToInput(r.courier_eur_per_kg), cmin: numToInput(r.courier_min_eur),
})

export default function LogisticsRates() {
  const { t } = useTranslation()
  const [f, setF] = useState<Form | null>(null)
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')
  useEffect(() => { api<Rates>('/api/admin/logistics-rates').then((r) => setF(toForm(r))).catch((x) => setErr(x instanceof ApiError ? t(x.messageKey) : t('errors.network'))) }, [t])

  if (!f) return <p role={err ? 'alert' : 'status'}>{err || t('common.loading')}</p>
  const set = (p: Partial<Form>) => setF({ ...f, ...p })
  const setBand = (i: number, p: Partial<Form['bands'][0]>) => set({ bands: f.bands.map((b, j) => (j === i ? { ...b, ...p } : b)) })

  async function save(e: FormEvent) {
    e.preventDefault(); setMsg(''); setErr('')
    if (!f) return
    const n = (s: string) => parseLocaleNumber(s)
    const body = {
      packaging_pct: n(f.pack), ltl_bands: f.bands.map((b) => ({ max_kg: n(b.max), eur_per_kg: n(b.rate) })),
      ftl_eur_per_truck: n(f.ftl), ftl_truck_capacity_kg: n(f.cap), courier_eur_per_kg: n(f.ckg), courier_min_eur: n(f.cmin),
    }
    const nums = [body.packaging_pct, body.ftl_eur_per_truck, body.ftl_truck_capacity_kg, body.courier_eur_per_kg, body.courier_min_eur, ...body.ltl_bands.flatMap((b) => [b.max_kg, b.eur_per_kg])]
    if (nums.some((x) => x === null)) return setErr(t('adminRates.invalid'))
    try { setF(toForm(await api<Rates>('/api/admin/logistics-rates', { method: 'PUT', json: body }))); setMsg(t('adminRates.saved')) }
    catch (x) { setErr(x instanceof ApiError && x.status === 422 ? t('adminRates.invalid') : x instanceof ApiError ? t(x.messageKey) : t('errors.network')) }
  }

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">{t('adminRates.title')}</h1>
      <p className="font-semibold bg-amber-50 border border-amber-300 rounded-md p-3">{t('adminRates.note')}</p>
      <form onSubmit={save} noValidate className="space-y-4">
        <Card className="space-y-3">
          <Field label={t('adminRates.packaging')}><Input inputMode="decimal" value={f.pack} onChange={(e) => set({ pack: e.target.value })} /></Field>
        </Card>
        <Card className="space-y-3">
          <h2 className="font-semibold">{t('adminRates.bands')}</h2>
          {f.bands.map((b, i) => (
            <div key={i} className="grid grid-cols-[1fr_1fr_auto] gap-2 items-end">
              <Field label={t('adminRates.maxKg')}><Input inputMode="decimal" value={b.max} onChange={(e) => setBand(i, { max: e.target.value })} /></Field>
              <Field label={t('adminRates.eurPerKg')}><Input inputMode="decimal" value={b.rate} onChange={(e) => setBand(i, { rate: e.target.value })} /></Field>
              <Button type="button" variant="secondary" disabled={f.bands.length < 2} onClick={() => set({ bands: f.bands.filter((_, j) => j !== i) })} aria-label={t('adminRates.removeBand')}>✕</Button>
            </div>
          ))}
          <Button type="button" variant="secondary" onClick={() => set({ bands: [...f.bands, { max: '', rate: '' }] })}>{t('adminRates.addBand')}</Button>
        </Card>
        <Card className="grid sm:grid-cols-2 gap-3">
          <h2 className="font-semibold sm:col-span-2">{t('adminRates.ftl')}</h2>
          <Field label={t('adminRates.ftlRate')}><Input inputMode="decimal" value={f.ftl} onChange={(e) => set({ ftl: e.target.value })} /></Field>
          <Field label={t('adminRates.ftlCap')}><Input inputMode="decimal" value={f.cap} onChange={(e) => set({ cap: e.target.value })} /></Field>
        </Card>
        <Card className="grid sm:grid-cols-2 gap-3">
          <h2 className="font-semibold sm:col-span-2">{t('adminRates.courier')}</h2>
          <Field label={t('adminRates.courierKg')}><Input inputMode="decimal" value={f.ckg} onChange={(e) => set({ ckg: e.target.value })} /></Field>
          <Field label={t('adminRates.courierMin')}><Input inputMode="decimal" value={f.cmin} onChange={(e) => set({ cmin: e.target.value })} /></Field>
        </Card>
        <Button type="submit">{t('adminRates.save')}</Button>
        {msg && <p role="status" className="font-semibold">{msg}</p>}
        {err && <p role="alert" className="text-brand font-semibold">{err}</p>}
      </form>
    </section>
  )
}
