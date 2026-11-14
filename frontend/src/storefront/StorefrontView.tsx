import type { LocalizedContent, Lang } from './types'

export type CompanyInfo = { name?: string; city?: string; logo_url?: string | null }

/** Minimal stub; Task 16 replaces the body and keeps these props. */
export default function StorefrontView({ config: c, template, lang, device = 'desktop' }: {
  config: LocalizedContent; template: string; lang: Lang; company?: CompanyInfo; device?: 'desktop' | 'mobile'
}) {
  return (
    <div lang={lang} data-template={template} data-device={device} className="bg-white text-navy p-4 space-y-4 text-sm">
      <h2 className="text-xl font-bold">{c.hero.headline}</h2>
      <p>{c.hero.subheadline}</p>
      <p>{c.about.story}</p>
      {c.products.map((p) => (
        <div key={p.product_id}>
          {p.photos[0] && <img src={p.photos[0]} alt={p.name ?? ''} className="w-full max-h-48 object-cover rounded" />}
          <h3 className="font-semibold">{p.name}</h3>
          <p>{p.short}</p>
        </div>
      ))}
      <ul className="list-disc pl-5">{c.why_us.map((w, i) => <li key={i}>{w}</li>)}</ul>
      <p>{[c.export_info.lead_time, c.export_info.sample_policy].filter(Boolean).join(' · ')}</p>
    </div>
  )
}
