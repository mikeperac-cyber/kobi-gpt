import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Field from '../../components/ui/Field'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import StorefrontView from '../../storefront/StorefrontView'
import type { Lang, LocalizedContent, SiteConfig, Storefront, Template } from '../../storefront/types'
import SectionEditor, { SECTIONS, type Section } from './SectionEditor'

type Tab = Lang | 'review'

export default function Editor({ initial, onPublished, onRestart }: {
  initial: Storefront
  onPublished(slug: string): void
  onRestart(): void
}) {
  const { t } = useTranslation()
  const [cfg, setCfg] = useState<SiteConfig>(initial.site_config)
  const [slug, setSlug] = useState(initial.slug)
  const [template, setTemplate] = useState<Template>(initial.template)
  const [tab, setTab] = useState<Tab>('de')
  const [device, setDevice] = useState<'desktop' | 'mobile'>('desktop')
  const [showPreview, setShowPreview] = useState(false)
  const [busy, setBusy] = useState<'' | 'save' | 'publish' | 'regen'>('')
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')

  const content = cfg[tab]
  const setContent = (c: LocalizedContent) => setCfg((x) => ({ ...x, [tab]: c }))
  const body = () => ({
    site_config: { ...cfg, template, de: clean(cfg.de), en: clean(cfg.en) },
    slug,
    template,
  })

  const save = async (): Promise<string | null> => {
    setBusy('save'); setErr(''); setMsg('')
    try {
      const r = await api<Storefront>('/api/storefronts/mine', { method: 'PUT', json: body() })
      setCfg((c) => ({ ...c, missing: r.site_config.missing }))
      setSlug(r.slug)
      setMsg(t('storefront.saved'))
      return r.slug
    } catch (x) {
      setErr(t(x instanceof ApiError ? x.messageKey : 'errors.network'))
      return null
    } finally { setBusy('') }
  }

  const publish = async () => {
    const saved = await save()
    if (!saved) return
    setBusy('publish')
    try {
      await api('/api/storefronts/mine/publish', { method: 'POST' })
      onPublished(saved)
    } catch (x) {
      setErr(t(x instanceof ApiError ? x.messageKey : 'errors.network'))
    } finally { setBusy('') }
  }

  const regen = async (section: Section, instruction?: string) => {
    if (tab === 'review') return
    if (!(await save())) return // server regenerates from the saved copy: persist local edits first
    setBusy('regen'); setErr(''); setMsg('')
    try {
      const r = await api<{ section: unknown; fallback: boolean; missing: string[] }>('/api/storefronts/mine/regenerate-section', {
        method: 'POST', json: { section, lang: tab, instruction: instruction ?? null },
      })
      if (r.fallback) setMsg(t('storefront.regenUnchanged'))
      else {
        setCfg((c) => ({ ...c, [tab]: { ...c[tab], [section]: r.section }, missing: r.missing }))
        setMsg(t('storefront.regenDone'))
      }
    } catch (x) {
      setErr(t(x instanceof ApiError ? x.messageKey : 'errors.network'))
    } finally { setBusy('') }
  }

  const tabs: [Tab, string][] = [['de', t('storefront.tabDe')], ['en', t('storefront.tabEn')],
    ['review', t('storefront.tabReview', { lang: cfg.review_language.toUpperCase() })]]
  const preview = (
    <div className="space-y-2">
      <div className="flex gap-2" role="group" aria-label={t('storefront.preview')}>
        {(['desktop', 'mobile'] as const).map((d) => (
          <Button key={d} type="button" variant={device === d ? 'primary' : 'secondary'} onClick={() => setDevice(d)}>{t(`storefront.${d}`)}</Button>
        ))}
      </div>
      <div className={`border border-slate-300 rounded-lg overflow-auto max-h-[75vh] bg-white ${device === 'mobile' ? 'w-[390px] max-w-full mx-auto rounded-[2rem] border-4 border-navy' : ''}`}>
        <StorefrontView config={tab === 'review' ? cfg.de : cfg[tab]} template={template} lang={tab === 'en' ? 'en' : 'de'} device={device} />
      </div>
    </div>
  )

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">{t('storefront.editorTitle')}</h1>
        <Button variant="secondary" onClick={onRestart}>{t('storefront.regenerateAll')}</Button>
      </div>
      <p className="text-sm text-slate-600 bg-slate-100 rounded-md p-3">{t('storefront.legalNote')}</p>
      <div className="grid lg:grid-cols-2 gap-6 items-start">
        <div className="space-y-4">
          <div role="tablist" className="flex gap-2 flex-wrap">
            {tabs.map(([k, label]) => (
              <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
                className={`min-h-11 px-4 rounded-md font-semibold border ${tab === k ? 'bg-navy text-white border-navy' : 'bg-white border-slate-300'}`}>{label}</button>
            ))}
          </div>
          {tab === 'review' && <p className="text-sm text-slate-600">{t('storefront.reviewNote')}</p>}
          <Field label={t('storefront.template')}>
            <Select value={template} onChange={(e) => setTemplate(e.target.value as Template)}>
              {(['industrial', 'natural', 'textile'] as const).map((k) => <option key={k} value={k}>{t(`storefront.tpl.${k}`)}</option>)}
            </Select>
          </Field>
          {SECTIONS.map((s) => (
            <SectionEditor key={`${tab}-${s}`} section={s} content={content} missing={cfg.missing} readOnly={tab === 'review'}
              regenBusy={busy !== ''} onChange={setContent} onRegen={(i) => void regen(s, i)} />
          ))}
          <Field label={t('storefront.slug')} hint={t('storefront.slugHint', { origin: window.location.origin })}>
            <Input value={slug} maxLength={60} onChange={(e) => setSlug(e.target.value)} />
          </Field>
          {cfg.missing.length > 0 && <p className="text-sm text-yellow-800">{t('storefront.missingCount', { n: cfg.missing.length })}</p>}
          {err && <p role="alert" className="text-brand font-semibold">{err}</p>}
          {msg && <p role="status" className="text-sm text-slate-700">{msg}</p>}
          <div className="flex flex-wrap gap-3">
            <Button variant="secondary" disabled={busy !== ''} onClick={() => void save()}>{busy === 'save' ? t('storefront.saving') : t('storefront.save')}</Button>
            <Button disabled={busy !== ''} onClick={() => void publish()}>{busy === 'publish' ? t('storefront.publishing') : t('storefront.publish')}</Button>
          </div>
        </div>
        <div>
          <Button type="button" variant="secondary" className="lg:hidden mb-3" aria-expanded={showPreview} onClick={() => setShowPreview(!showPreview)}>
            {t(showPreview ? 'storefront.hidePreview' : 'storefront.showPreview')}
          </Button>
          <div className={`${showPreview ? '' : 'hidden'} lg:block lg:sticky lg:top-4`}>{preview}</div>
        </div>
      </div>
    </div>
  )
}

/** Drop blank why_us lines before saving (the textarea keeps them while typing). */
const clean = (c: LocalizedContent): LocalizedContent => ({ ...c, why_us: c.why_us.filter((x) => x.trim()) })
