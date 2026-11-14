import { useTranslation } from 'react-i18next'
import Button from '../../components/ui/Button'
import Field from '../../components/ui/Field'
import Select from '../../components/ui/Select'
import type { Params } from './types'

export type ProductOpt = { id: string; name_tr: string }

export default function ComplianceStart({ products, productId, onProduct, params, onParams, isFood, hasReport, busy, onStart }: {
  products: ProductOpt[]; productId: string; onProduct(id: string): void
  params: Params; onParams(p: Params): void; isFood: boolean; hasReport: boolean; busy: boolean; onStart(): void
}) {
  const { t } = useTranslation()
  if (products.length === 0) return <p>{t('compliance.noProducts')}</p>
  const set = (p: Partial<Params>) => onParams({ ...params, ...p })
  return (
    <form className="space-y-5 max-w-xl" onSubmit={(e) => { e.preventDefault(); onStart() }}>
      <Field label={t('compliance.product')}>
        <Select value={productId} onChange={(e) => onProduct(e.target.value)}>
          {products.map((p) => <option key={p.id} value={p.id}>{p.name_tr}</option>)}
        </Select>
      </Field>
      <fieldset className="space-y-2">
        <legend className="text-sm font-semibold">{t('compliance.channel')}</legend>
        {(['b2b', 'b2c'] as const).map((c) => (
          <label key={c} className="flex items-center gap-3 min-h-11">
            <input type="radio" name="channel" className="w-5 h-5" checked={params.channel === c} onChange={() => set({ channel: c })} />
            {t(c === 'b2b' ? 'compliance.channelB2b' : 'compliance.channelB2c')}
          </label>
        ))}
      </fieldset>
      {isFood && (
        <fieldset className="space-y-2">
          <legend className="text-sm font-semibold">{t('compliance.processing')}</legend>
          {(['roasted', 'raw'] as const).map((v) => (
            <label key={v} className="flex items-center gap-3 min-h-11">
              <input type="radio" name="processing" className="w-5 h-5" checked={params.processing === v} onChange={() => set({ processing: v })} />
              {t(v === 'roasted' ? 'compliance.processingRoasted' : 'compliance.processingRaw')}
            </label>
          ))}
        </fieldset>
      )}
      <div>
        <label className="flex items-center gap-3 min-h-11">
          <input type="checkbox" className="w-5 h-5" checked={params.structural} onChange={(e) => set({ structural: e.target.checked })} aria-describedby="structural-help" />
          {t('compliance.structural')}
        </label>
        <p id="structural-help" className="text-sm text-slate-600">{t('compliance.structuralHelp')}</p>
      </div>
      <Button type="submit" disabled={busy || !productId || (isFood && !params.processing)}>{t(hasReport ? 'compliance.rerun' : 'compliance.start')}</Button>
    </form>
  )
}
