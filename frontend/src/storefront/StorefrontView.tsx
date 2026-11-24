import type { ReactNode } from 'react'
import type { LocalizedContent, Lang } from './types'
import { STR } from './strings'
import { THEMES } from './themes'

export type Trust = {
  company_verified: boolean; verified_at: string | null
  certificates: { name: string; verified: boolean; valid_until: string | null }[]
}
export type CompanyInfo = { name?: string | null; city?: string | null; logo_url?: string | null; trust?: Trust }

const fold = (x: string) => x.toLocaleLowerCase('tr').trim()
const day = (iso: string, lang: Lang) => new Date(`${iso}T00:00:00`).toLocaleDateString(lang === 'de' ? 'de-DE' : 'en-GB')

/** Pure renderer shared by the public page and the producer editor preview. Null values never render. */
export default function StorefrontView({ config: c, template, lang, company, device = 'desktop', rfq, footer, whatsapp }: {
  config: LocalizedContent; template: string; lang: Lang; company?: CompanyInfo
  device?: 'desktop' | 'mobile'; rfq?: ReactNode; footer?: ReactNode; whatsapp?: string | null
}) {
  const t = THEMES[template] ?? THEMES.industrial
  const s = STR[lang]
  const grid = device === 'mobile' ? 'grid-cols-1' : `grid-cols-1 ${t.grid}`
  const heroPhoto = c.products.find((p) => p.photos[0])?.photos[0]
  const facts = [
    c.about.city ?? company?.city, c.about.founded_year ? `${s.founded} ${c.about.founded_year}` : null,
    c.about.team_size ? `${s.team}: ${c.about.team_size}` : null,
  ].filter(Boolean)
  const exp = [
    c.export_info.incoterms.length ? [s.incoterms, c.export_info.incoterms.join(', ')] : null,
    c.export_info.lead_time ? [s.leadTime, c.export_info.lead_time] : null,
    c.export_info.sample_policy ? [s.samples, c.export_info.sample_policy] : null,
  ].filter(Boolean) as string[][]
  const h2 = `text-2xl mb-5 ${t.h}`

  return (
    <div lang={lang} data-template={template} className={`${t.page} text-base leading-relaxed`}>
      <header className={`${t.hero} px-4 py-10 sm:py-16`}>
        <div className={`max-w-5xl mx-auto grid gap-8 items-center ${device === 'mobile' ? '' : 'sm:grid-cols-2'}`}>
          <div>
            {company?.name && (
              <p className="flex items-center gap-2 mb-4 font-semibold">
                {company.logo_url && <img src={company.logo_url} alt="" width={32} height={32} className="h-8 w-8 object-contain bg-white rounded" />}
                {company.name}
              </p>
            )}
            {company?.trust?.company_verified && company.trust.verified_at && (
              <p className="inline-flex items-center gap-1.5 mb-4 rounded-full bg-green-100 text-green-900 text-sm font-semibold px-3 py-1">
                <span aria-hidden>✓</span>{s.verifiedSupplier.replace('{date}', day(company.trust.verified_at, lang))}
              </p>
            )}
            {c.hero.headline && <h1 className="text-3xl sm:text-4xl font-bold leading-tight">{c.hero.headline}</h1>}
            {c.hero.subheadline && <p className={`mt-4 text-lg ${t.heroSub}`}>{c.hero.subheadline}</p>}
            {((c.hero.cta && rfq) || whatsapp) && (
              <div className="flex flex-wrap gap-3 mt-6">
                {c.hero.cta && rfq && <a href="#rfq" className={`${t.btn} inline-block`}>{c.hero.cta}</a>}
                {whatsapp && <a href={whatsapp} target="_blank" rel="noopener noreferrer" className={`${t.btn} inline-block opacity-90`}>{s.whatsapp}</a>}
              </div>
            )}
          </div>
          {heroPhoto && <img src={heroPhoto} alt="" width={800} height={600} loading="eager" decoding="async" fetchPriority="high" className="w-full aspect-[4/3] object-cover rounded-lg" />}
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-10 space-y-12">
        {c.products.length > 0 && (
          <section>
            <h2 className={h2}>{s.products}</h2>
            <div className={`grid gap-5 ${grid}`}>
              {c.products.map((p) => (
                <article key={p.product_id} className={`${t.card} overflow-hidden`}>
                  {p.photos[0] && <img src={p.photos[0]} alt={p.name ?? ''} width={600} height={450} loading="lazy" decoding="async" className={`w-full ${t.photo} object-cover`} />}
                  <div className="p-4 space-y-2">
                    {p.name && <h3 className="text-lg font-semibold">{p.name}</h3>}
                    {p.short && <p>{p.short}</p>}
                    {p.long && <p className={t.muted}>{p.long}</p>}
                    {p.specs.length > 0 && (
                      <dl className="text-sm grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
                        {p.specs.map((sp, k) => <div key={k} className="contents"><dt className={t.muted}>{sp.label}</dt><dd>{sp.value}</dd></div>)}
                      </dl>
                    )}
                    {(p.moq || p.packaging) && <p className="text-sm">{[p.moq, p.packaging].filter(Boolean).join(' · ')}</p>}
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}

        {(c.about.story || facts.length > 0 || c.about.certifications.length > 0) && (
          <section className={`${t.section} pt-2`}>
            <h2 className={h2}>{s.about}</h2>
            {c.about.story && <p className="max-w-3xl">{c.about.story}</p>}
            {facts.length > 0 && <p className={`mt-3 ${t.muted}`}>{facts.join(' · ')}</p>}
            {c.about.certifications.length > 0 && (
              <p className="mt-3 flex flex-wrap gap-2 items-center"><span className="font-semibold">{s.certs}:</span>
                {c.about.certifications.map((x) => {
                  // with trust (public page): every certificate says whether a document was checked; editor preview has none
                  const v = company?.trust?.certificates.find((cert) => fold(cert.name) === fold(x))
                  const label = !company?.trust ? x
                    : v?.verified ? `✓ ${x} · ${s.certChecked}${v.valid_until ? `, ${s.validUntil} ${day(v.valid_until, lang)}` : ''}`
                    : `${x} · ${s.selfDeclared}`
                  return <span key={x} className={`${t.chip} text-sm rounded-full px-3 py-1 ${v?.verified ? 'ring-1 ring-green-700' : ''}`}>{label}</span>
                })}
              </p>
            )}
          </section>
        )}

        {c.why_us.length > 0 && (
          <section>
            <h2 className={h2}>{s.whyUs}</h2>
            <ul className="grid gap-3 sm:grid-cols-2">
              {c.why_us.map((w, i) => <li key={i} className={`${t.card} p-4`}>{w}</li>)}
            </ul>
          </section>
        )}

        {exp.length > 0 && (
          <section>
            <h2 className={h2}>{s.exportInfo}</h2>
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
              {exp.map(([k, v]) => <div key={k} className="contents"><dt className="font-semibold">{k}</dt><dd>{v}</dd></div>)}
            </dl>
          </section>
        )}

        {rfq && (
          <section id="rfq" className={`${t.card} p-5 sm:p-8 scroll-mt-4`}>
            {c.rfq.title && <h2 className={`text-2xl mb-2 ${t.h}`}>{c.rfq.title}</h2>}
            {c.rfq.intro && <p className={`mb-5 ${t.muted}`}>{c.rfq.intro}</p>}
            {rfq}
            {whatsapp && <p className="mt-4"><a href={whatsapp} target="_blank" rel="noopener noreferrer" className="underline font-semibold">{s.whatsapp}</a></p>}
          </section>
        )}
      </main>

      <footer className={`border-t border-black/10 ${t.muted} text-sm px-4 py-8`}>
        <div className="max-w-5xl mx-auto space-y-2">
          {c.footer.note && <p>{c.footer.note}</p>}
          {footer}
        </div>
      </footer>
    </div>
  )
}
