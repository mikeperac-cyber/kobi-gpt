import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import PhotoPicker from '../../components/PhotoPicker'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Textarea from '../../components/ui/Textarea'
import type { LocalizedContent } from '../../storefront/types'

export const SECTIONS = ['hero', 'about', 'products', 'why_us', 'export_info', 'rfq', 'footer', 'seo'] as const
export type Section = (typeof SECTIONS)[number]

type Def = { path: string; label: string; area?: boolean }
const FIELDS: Partial<Record<Section, Def[]>> = {
  hero: [{ path: 'hero.headline', label: 'headline' }, { path: 'hero.subheadline', label: 'subheadline' }, { path: 'hero.cta', label: 'cta' }],
  about: [{ path: 'about.story', label: 'story', area: true }],
  export_info: [{ path: 'export_info.lead_time', label: 'leadTime' }, { path: 'export_info.sample_policy', label: 'samplePolicy' }],
  rfq: [{ path: 'rfq.title', label: 'title' }, { path: 'rfq.intro', label: 'intro', area: true }],
  footer: [{ path: 'footer.note', label: 'note' }],
  seo: [{ path: 'seo.title', label: 'seoTitle' }, { path: 'seo.description', label: 'seoDescription', area: true }],
}
const PRODUCT_FIELDS: Def[] = [
  { path: 'name', label: 'name' }, { path: 'short', label: 'short' }, { path: 'long', label: 'long', area: true },
  { path: 'moq', label: 'moq' }, { path: 'packaging', label: 'packaging' },
]

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const get = (o: any, path: string): any => path.split('.').reduce((a, k) => a?.[k], o)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const set = (o: any, path: string, v: unknown): any => {
  const [k, ...rest] = path.split('.')
  const copy = Array.isArray(o) ? [...o] : { ...o }
  copy[k] = rest.length ? set(o[k], rest.join('.'), v) : v
  return copy
}

export default function SectionEditor({ section, content, missing, readOnly, regenBusy, note, onChange, onRegen }: {
  section: Section
  content: LocalizedContent
  missing: string[]
  readOnly: boolean
  regenBusy: boolean
  note?: boolean
  onChange(next: LocalizedContent): void
  onRegen?(instruction?: string): void
}) {
  const { t } = useTranslation()
  const [instr, setInstr] = useState<string | null>(null)

  const field = (path: string, label: string, area: boolean | undefined, abs: string) => {
    const value: string = get(content, abs) ?? ''
    const flag = missing.includes(abs) && !value.trim()
    const props = {
      value, readOnly, 'aria-label': t(`storefront.f.${label}`),
      className: flag ? '!bg-yellow-100 !border-yellow-500' : readOnly ? 'bg-slate-50' : '',
      onChange: (e: { target: { value: string } }) => onChange(set(content, abs, e.target.value)),
    }
    return (
      <div key={path} className="space-y-1">
        <label className="block text-sm font-semibold">{t(`storefront.f.${label}`)}</label>
        {area ? <Textarea rows={4} {...props} /> : <Input {...props} />}
        {flag && <p className="text-sm text-yellow-800">{t('storefront.mustEnter')}</p>}
      </div>
    )
  }

  const whyFlag = section === 'why_us' && missing.includes('why_us') && content.why_us.filter((x) => x.trim()).length < 3

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-bold">{t(`storefront.sections.${section}`)}</h3>
        {!readOnly && onRegen && (
          <Button type="button" variant="secondary" disabled={regenBusy} onClick={() => onRegen(instr?.trim() || undefined)}>
            {t('storefront.regen')}
          </Button>
        )}
      </div>
      <p aria-live="polite" className="text-sm text-slate-500 empty:hidden">{note ? t('storefront.regenUnchanged') : ''}</p>
      {!readOnly && onRegen && (
        <input type="text" maxLength={200} value={instr ?? ''} onChange={(e) => setInstr(e.target.value)}
          aria-label={t('storefront.instruction')} placeholder={t('storefront.instructionPh')}
          className="w-full min-h-11 px-3 rounded-md border border-slate-300 bg-white focus:outline-2 focus:outline-navy" />
      )}
      {!readOnly && onRegen && (
        <div className="flex gap-2" role="group" aria-label={t('storefront.regen')}>
          {(['regenShorter', 'regenTechnical'] as const).map((k) => {
            const v = t(`storefront.${k}`)
            return (
              <button key={k} type="button" aria-pressed={instr === v} onClick={() => setInstr(instr === v ? null : v)}
                className={`min-h-9 px-3 rounded-full text-sm border ${instr === v ? 'bg-navy text-white border-navy' : 'bg-white border-slate-300'}`}>
                {v}
              </button>
            )
          })}
        </div>
      )}
      {section === 'products' ? content.products.map((p, i) => (
        <div key={p.product_id} className="space-y-3 border-t border-slate-100 pt-3">
          {PRODUCT_FIELDS.map((d) => field(`${i}.${d.path}`, d.label, d.area, `products.${i}.${d.path}`))}
          {!readOnly && (
            <div>
              <p className="text-sm font-semibold">{t('storefront.photos')}</p>
              <PhotoPicker urls={p.photos} onChange={(urls) => onChange(set(content, `products.${i}.photos`, urls))} />
            </div>
          )}
        </div>
      )) : section === 'why_us' ? (
        <div className="space-y-1">
          <label className="block text-sm font-semibold">{t('storefront.f.whyUs')}</label>
          <Textarea rows={4} readOnly={readOnly} value={content.why_us.join('\n')} aria-label={t('storefront.f.whyUs')}
            className={whyFlag ? '!bg-yellow-100 !border-yellow-500' : readOnly ? 'bg-slate-50' : ''}
            onChange={(e) => onChange({ ...content, why_us: e.target.value.split('\n').slice(0, 4) })} />
          {whyFlag && <p className="text-sm text-yellow-800">{t('storefront.mustEnter')}</p>}
        </div>
      ) : (FIELDS[section] ?? []).map((d) => field(d.path, d.label, d.area, d.path))}
      {section === 'export_info' && (
        <fieldset className={`rounded-md p-2 ${missing.includes('export_info.incoterms') && !content.export_info.incoterms.length ? 'bg-yellow-100' : ''}`}>
          <legend className="text-sm font-semibold">{t('storefront.incoterms')}</legend>
          <div className="flex flex-wrap gap-x-4">
            {['EXW', 'FCA', 'FOB', 'CIF', 'DAP'].map((i) => (
              <label key={i} className="flex items-center gap-2 min-h-11">
                <input type="checkbox" disabled={readOnly} checked={content.export_info.incoterms.includes(i)}
                  onChange={(e) => onChange(set(content, 'export_info.incoterms', e.target.checked ? [...content.export_info.incoterms, i] : content.export_info.incoterms.filter((x) => x !== i)))} />
                {i}
              </label>
            ))}
          </div>
          {missing.includes('export_info.incoterms') && !content.export_info.incoterms.length && <p className="text-sm text-yellow-800">{t('storefront.mustEnter')}</p>}
        </fieldset>
      )}
    </section>
  )
}
