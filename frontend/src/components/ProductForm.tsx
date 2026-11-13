import { useTranslation } from 'react-i18next'
import { numToInput, parseLocaleNumber } from '../i18n/format'
import PhotoPicker from './PhotoPicker'
import type { Errs } from './CompanyFields'
import Field from './ui/Field'
import Input from './ui/Input'
import Select from './ui/Select'
import Textarea from './ui/Textarea'

export const UNITS = ['kg', 'adet', 'metre', 'koli'] as const

export interface ProductDraft {
  name_tr: string; description_tr: string; material_or_ingredients: string; unit: string
  moq: string; unit_weight_kg: string; price_floor: string; photos: string[]
}
export const emptyProduct: ProductDraft = {
  name_tr: '', description_tr: '', material_or_ingredients: '', unit: 'kg', moq: '', unit_weight_kg: '', price_floor: '', photos: [],
}
export interface ProductDoc {
  id: string; name_tr: string; description_tr: string; material_or_ingredients: string; unit: string
  moq: number; unit_weight_kg: number | null; price_floor: number; photos: string[]
}
export const productFromDoc = (p: ProductDoc): ProductDraft => ({
  name_tr: p.name_tr, description_tr: p.description_tr, material_or_ingredients: p.material_or_ingredients, unit: p.unit,
  moq: numToInput(p.moq), unit_weight_kg: numToInput(p.unit_weight_kg), price_floor: numToInput(p.price_floor), photos: p.photos,
})

/** Client-side check + payload. Photos are required only while onboarding (the API enforces the same). */
export function productPayload(d: ProductDraft, mode: 'onboarding' | 'edit'): { payload: Record<string, unknown>; errs: Record<string, string> } {
  const errs: Record<string, string> = {}
  const moq = parseLocaleNumber(d.moq)
  const floor = parseLocaleNumber(d.price_floor)
  const weight = d.unit_weight_kg.trim() ? parseLocaleNumber(d.unit_weight_kg) : null
  if (!d.name_tr.trim()) errs.name_tr = 'company.errRequired'
  if (moq === null || moq <= 0) errs.moq = 'products.errPositive'
  if (floor === null || floor <= 0) errs.price_floor = 'products.errPositive'
  if (d.unit_weight_kg.trim() && (weight === null || weight <= 0)) errs.unit_weight_kg = 'products.errPositive'
  if (mode === 'onboarding' && !d.photos.length) errs.photos = 'errors.photo_required'
  return {
    errs,
    payload: {
      name_tr: d.name_tr.trim(), description_tr: d.description_tr.trim(), material_or_ingredients: d.material_or_ingredients.trim(),
      unit: d.unit, moq, unit_weight_kg: weight, price_floor: floor, photos: d.photos,
    },
  }
}

function Lock() {
  return (
    <svg aria-hidden viewBox="0 0 24 24" className="inline size-4 mr-1 -mt-0.5 fill-none stroke-current" strokeWidth={2}>
      <rect x="5" y="11" width="14" height="9" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </svg>
  )
}

export default function ProductForm({ value: v, onChange, mode, errs = {} }: {
  value: ProductDraft; onChange(v: ProductDraft): void; mode: 'onboarding' | 'edit'; errs?: Errs
}) {
  const { t } = useTranslation()
  const bind = (k: Exclude<keyof ProductDraft, 'photos'>) => ({
    value: v[k], onChange: (e: { target: { value: string } }) => onChange({ ...v, [k]: e.target.value }),
  })
  return (
    <div className="space-y-4">
      <Field label={t('products.name')} error={errs.name_tr}><Input required {...bind('name_tr')} /></Field>
      <Field label={t('products.description')} hint={t('products.descriptionHint')} error={errs.description_tr}>
        <Textarea {...bind('description_tr')} />
      </Field>
      <Field label={t('products.material')} hint={t('products.materialHint')} error={errs.material_or_ingredients}><Input {...bind('material_or_ingredients')} /></Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label={t('products.unit')} error={errs.unit}>
          <Select {...bind('unit')}>{UNITS.map((u) => <option key={u} value={u}>{t(`products.units.${u}`)}</option>)}</Select>
        </Field>
        <Field label={t('products.moq')} hint={t('products.moqHint')} error={errs.moq}><Input inputMode="decimal" {...bind('moq')} /></Field>
      </div>
      <Field label={t('products.unitWeight')} hint={t('products.unitWeightHint')} error={errs.unit_weight_kg}><Input inputMode="decimal" {...bind('unit_weight_kg')} /></Field>
      <Field label={t('products.floor')} hint={<><Lock />{t('products.floorTip')}</>} error={errs.price_floor}>
        <Input inputMode="decimal" className="bg-slate-50 border-navy/40" {...bind('price_floor')} />
      </Field>
      <div>
        <p className="text-sm font-semibold">{t('products.photos')}{mode === 'onboarding' && <span className="text-brand"> *</span>}</p>
        <PhotoPicker urls={v.photos} max={6} onChange={(photos) => onChange({ ...v, photos })} />
        {errs.photos && <p role="alert" className="text-sm text-brand font-semibold">{errs.photos}</p>}
      </div>
    </div>
  )
}
