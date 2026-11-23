import { useEffect, useState, type ReactNode } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import RfqForm from './RfqForm'
import StorefrontView from './StorefrontView'
import { waLink } from './whatsapp'
import { STR, type PublicCompany, type PublicLegal } from './strings'
import type { Lang, LocalizedContent } from './types'

export type PublicData = {
  slug: string; site_config: { de: LocalizedContent; en: LocalizedContent; template: string }
  company: PublicCompany; legal: PublicLegal
}

export function usePublic() {
  const { slug = '' } = useParams()
  const [sp, setSp] = useSearchParams()
  const lang: Lang = sp.get('lang') === 'en' ? 'en' : 'de'
  const [data, setData] = useState<PublicData | null>(null)
  const [err, setErr] = useState<'notFound' | 'loadError' | null>(null)
  useEffect(() => {
    let live = true
    api<PublicData>(`/api/public/storefronts/${encodeURIComponent(slug)}`)
      .then((d) => live && setData(d))
      .catch((e) => live && setErr(e instanceof ApiError && e.status === 404 ? 'notFound' : 'loadError'))
    return () => { live = false }
  }, [slug])
  useEffect(() => { document.documentElement.lang = lang }, [lang])
  return { slug, lang, data, err, setLang: (l: Lang) => setSp(l === 'de' ? {} : { lang: l }, { replace: true }) }
}

export function LangSwitch({ lang, onChange }: { lang: Lang; onChange: (l: Lang) => void }) {
  return (
    <div className="flex justify-end gap-1 px-4 py-2 bg-white text-sm border-b border-slate-200" role="group" aria-label={STR[lang].langLabel}>
      {(['de', 'en'] as const).map((l) => (
        <button key={l} onClick={() => onChange(l)} aria-pressed={lang === l}
          className={`min-h-9 px-3 rounded font-semibold ${lang === l ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'}`}>
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  )
}

function setMeta(attr: 'name' | 'property', key: string, content: string) {
  let el = document.head.querySelector<HTMLMetaElement>(`meta[${attr}="${key}"]`)
  if (!el) { el = document.createElement('meta'); el.setAttribute(attr, key); document.head.appendChild(el) }
  el.content = content
}

function useHead(d: PublicData | null, lang: Lang, page?: string) {
  useEffect(() => {
    if (!d) return
    const c = d.site_config[lang]
    const title = [page, c.seo.title ?? d.company.name].filter(Boolean).join(' | ')
    document.title = title
    const desc = c.seo.description ?? c.hero.subheadline ?? ''
    const img = c.products.find((p) => p.photos[0])?.photos[0] ?? d.company.logo_url
    setMeta('name', 'description', desc)
    setMeta('property', 'og:title', title)
    setMeta('property', 'og:description', desc)
    if (img) setMeta('property', 'og:image', new URL(img, location.origin).href)
    if (d.company.logo_url) {
      let l = document.head.querySelector<HTMLLinkElement>('link[rel="icon"]')
      if (!l) { l = document.createElement('link'); l.rel = 'icon'; document.head.appendChild(l) }
      l.removeAttribute('type'); l.href = d.company.logo_url
    }
  }, [d, lang, page])
}

export function PublicShell({ children, page }: { children: (p: { data: PublicData; lang: Lang; slug: string }) => ReactNode; page?: string }) {
  const { slug, lang, data, err, setLang } = usePublic()
  useHead(data, lang, page)
  const s = STR[lang]
  if (err) return <p className="p-8 text-center">{err === 'notFound' ? s.notFound : s.loadError}</p>
  if (!data) return <p className="p-8 text-center" role="status">{s.loading}</p>
  return <><LangSwitch lang={lang} onChange={setLang} />{children({ data, lang, slug })}</>
}

export default function PublicStorefront() {
  return (
    <PublicShell>
      {({ data, lang, slug }) => {
        const cfg = data.site_config[lang]
        const q = lang === 'en' ? '?lang=en' : ''
        const link = 'underline mr-4 inline-block py-2'
        return (
          <StorefrontView
            config={cfg} template={data.site_config.template} lang={lang} company={data.company}
            whatsapp={waLink(data.company.whatsapp, STR[lang].waText.replace('{url}', location.href))}
            rfq={<RfqForm key={lang} slug={slug} lang={lang} productNames={cfg.products.map((p) => p.name).filter((n): n is string => !!n)} />}
            footer={<nav><Link className={link} to={`/s/${slug}/impressum${q}`}>{STR[lang].imprint}</Link><Link className={link} to={`/s/${slug}/datenschutz${q}`}>{STR[lang].privacy}</Link></nav>}
          />
        )
      }}
    </PublicShell>
  )
}
