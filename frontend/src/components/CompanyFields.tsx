import { useTranslation } from 'react-i18next'
import { ApiError } from '../api/client'
import { CERTS } from '../data/certifications'
import { PROVINCES } from '../data/provinces'
import { numToInput, parseLocaleNumber } from '../i18n/format'
import PhotoPicker from './PhotoPicker'
import Field from './ui/Field'
import Input from './ui/Input'
import Select from './ui/Select'
import Textarea from './ui/Textarea'

export type Errs = Record<string, string>
export const SECTORS = ['tekstil', 'gida', 'otomotiv_yan_sanayi', 'diger'] as const

export interface CompanyDraft {
  name: string; city: string; sector: string; description_tr: string
  founded_year: string; employee_count: string; certifications: string[]
  phone: string; email: string; website: string; logo_url: string | null; min_order_note: string
}

export const emptyCompany: CompanyDraft = {
  name: '', city: '', sector: '', description_tr: '', founded_year: '', employee_count: '', certifications: [],
  phone: '', email: '', website: '', logo_url: null, min_order_note: '',
}

export interface CompanyDoc {
  name: string; city: string; sector: string; description_tr: string; founded_year: number; employee_count: number
  certifications: string[]; contact: { phone: string; email: string; website: string | null }
  logo_url: string | null; min_order_note: string
}

export const companyFromDoc = (c: CompanyDoc): CompanyDraft => ({
  name: c.name, city: c.city, sector: c.sector, description_tr: c.description_tr,
  founded_year: numToInput(c.founded_year), employee_count: numToInput(c.employee_count),
  certifications: c.certifications, phone: c.contact.phone, email: c.contact.email,
  website: c.contact.website ?? '', logo_url: c.logo_url, min_order_note: c.min_order_note,
})

/** Client-side check (same rules as the API) + the payload to send. Error values are i18n keys. */
export function companyPayload(d: CompanyDraft): { payload: Record<string, unknown>; errs: Record<string, string> } {
  const errs: Record<string, string> = {}
  const year = parseLocaleNumber(d.founded_year)
  const staff = parseLocaleNumber(d.employee_count)
  if (!d.name.trim()) errs.name = 'company.errRequired'
  if (!d.city) errs.city = 'company.errRequired'
  if (!d.sector) errs.sector = 'company.errRequired'
  if (year === null || !Number.isInteger(year) || year < 1800 || year > new Date().getFullYear()) errs.founded_year = 'company.errYear'
  if (staff === null || !Number.isInteger(staff) || staff < 1) errs.employee_count = 'company.errStaff'
  if (d.phone.trim().length < 3) errs['contact.phone'] = 'company.errRequired'
  if (!/^\S+@\S+$/.test(d.email.trim())) errs['contact.email'] = 'company.errEmail'
  return {
    errs,
    payload: {
      name: d.name.trim(), city: d.city, sector: d.sector, description_tr: d.description_tr.trim(),
      founded_year: year, employee_count: staff, certifications: d.certifications,
      contact: { phone: d.phone.trim(), email: d.email.trim(), website: d.website.trim() || null },
      logo_url: d.logo_url, min_order_note: d.min_order_note.trim(),
    },
  }
}

/** i18n keys -> translated strings, for passing to Field `error`. */
export const translateErrs = (t: (k: string) => string, keys: Record<string, string>): Errs =>
  Object.fromEntries(Object.entries(keys).map(([f, k]) => [f, t(k)]))

/** API error -> per-field keys (fields like "company.name" are filtered by prefix and stripped) + a top-level key if no field. */
export function serverErrs(x: unknown, prefix = ''): { fields: Record<string, string>; top: string } {
  if (!(x instanceof ApiError)) return { fields: {}, top: 'errors.network' }
  const own = x.fields.filter((f) => f.startsWith(prefix)).map((f) => f.slice(prefix.length))
  return { fields: Object.fromEntries(own.map((f) => [f, x.messageKey])), top: x.fields.length ? '' : x.messageKey }
}

type TextKey = 'name' | 'phone' | 'email' | 'website' | 'min_order_note' | 'founded_year' | 'employee_count'

export default function CompanyFields({ value: v, onChange, errs }: { value: CompanyDraft; onChange(v: CompanyDraft): void; errs: Errs }) {
  const { t } = useTranslation()
  const set = <K extends keyof CompanyDraft>(k: K, x: CompanyDraft[K]) => onChange({ ...v, [k]: x })
  const txt = (k: TextKey) => ({ value: v[k], onChange: (e: { target: { value: string } }) => set(k, e.target.value) })
  const toggle = (c: string) => set('certifications', v.certifications.includes(c) ? v.certifications.filter((x) => x !== c) : [...v.certifications, c])

  return (
    <div className="space-y-4">
      <Field label={t('company.name')} error={errs.name}><Input required autoComplete="organization" {...txt('name')} /></Field>
      <div>
        <p className="text-sm font-semibold">{t('company.logo')}</p>
        <p className="text-sm text-slate-600 mb-1">{t('company.logoHint')}</p>
        <PhotoPicker urls={v.logo_url ? [v.logo_url] : []} max={1} prefix="logos" onChange={(u) => set('logo_url', u[0] ?? null)} />
      </div>
      <Field label={t('company.city')} error={errs.city}>
        <Select value={v.city} onChange={(e) => set('city', e.target.value)}>
          <option value="">{t('company.cityPlaceholder')}</option>
          {PROVINCES.map((p) => <option key={p} value={p}>{p}</option>)}
        </Select>
      </Field>
      <Field label={t('company.sector')} error={errs.sector}>
        <Select value={v.sector} onChange={(e) => set('sector', e.target.value)}>
          <option value="">{t('company.sectorPlaceholder')}</option>
          {SECTORS.map((s) => <option key={s} value={s}>{t(`company.sectors.${s}`)}</option>)}
        </Select>
      </Field>
      <Field label={t('company.description')} hint={t('company.descriptionHint')} error={errs.description_tr}>
        <Textarea value={v.description_tr} onChange={(e) => set('description_tr', e.target.value)} />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label={t('company.founded')} error={errs.founded_year}><Input inputMode="numeric" {...txt('founded_year')} /></Field>
        <Field label={t('company.employees')} error={errs.employee_count}><Input inputMode="numeric" {...txt('employee_count')} /></Field>
      </div>
      <fieldset>
        <legend className="text-sm font-semibold">{t('company.certs')}</legend>
        <p className="text-sm text-slate-600">{t('company.certsHint')}</p>
        <div className="grid grid-cols-1 min-[420px]:grid-cols-2 gap-x-3">
          {CERTS.map((c) => (
            <label key={c} className="flex items-center gap-3 min-h-11 text-sm">
              <input type="checkbox" checked={v.certifications.includes(c)} onChange={() => toggle(c)} className="size-5 accent-brand" />
              {t(`company.certNames.${c}`)}
            </label>
          ))}
        </div>
        {errs.certifications && <p role="alert" className="text-sm text-brand">{errs.certifications}</p>}
      </fieldset>
      <Field label={t('company.phone')} error={errs['contact.phone']}><Input type="tel" autoComplete="tel" {...txt('phone')} /></Field>
      <Field label={t('company.email')} error={errs['contact.email']}><Input type="email" autoComplete="email" {...txt('email')} /></Field>
      <Field label={t('company.website')} hint={t('common.optional')} error={errs['contact.website']}><Input type="url" inputMode="url" {...txt('website')} /></Field>
      <Field label={t('company.minOrder')} hint={t('company.minOrderHint')} error={errs.min_order_note}><Input {...txt('min_order_note')} /></Field>
    </div>
  )
}
