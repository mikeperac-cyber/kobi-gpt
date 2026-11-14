import { Link } from 'react-router-dom'
import { PublicShell } from './PublicStorefront'
import { STR, type PublicLegal } from './strings'
import type { Lang } from './types'

const dash = '—'

function Imprint({ l, lang }: { l: PublicLegal; lang: Lang }) {
  const s = STR[lang].legal
  const rows: [string, string | null][] = [
    [s.provider, l.name], [s.address, l.address], [s.phone, l.phone], [s.email, l.email], [s.web, l.website],
    [s.rep, l.representative], [s.register, l.register],
  ]
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-3">
      {rows.map(([k, v]) => <div key={k} className="contents"><dt className="font-semibold">{k}</dt><dd>{v ?? dash}</dd></div>)}
    </dl>
  )
}

export default function LegalPage({ kind }: { kind: 'impressum' | 'datenschutz' }) {
  const title = (lang: Lang) => (kind === 'impressum' ? STR[lang].imprint : STR[lang].privacy)
  return (
    <PublicShell page={undefined}>
      {({ data, lang, slug }) => {
        const l = data.legal
        const contact = [l.address, l.phone, l.email].filter(Boolean).join(', ') || dash
        return (
          <div className="bg-white text-slate-900 min-h-screen px-4 py-10">
            <main lang={lang} className="max-w-2xl mx-auto space-y-4">
              <Link to={`/s/${slug}${lang === 'en' ? '?lang=en' : ''}`} className="underline">&larr; {STR[lang].back}</Link>
              <h1 className="text-3xl font-bold">{title(lang)}</h1>
              {kind === 'impressum'
                ? <Imprint l={l} lang={lang} />
                : STR[lang].privacyBody({ name: l.name ?? dash, contact }).map((b) => (
                  <section key={b.h}><h2 className="text-lg font-semibold mt-4">{b.h}</h2><p>{b.p}</p></section>
                ))}
            </main>
          </div>
        )
      }}
    </PublicShell>
  )
}
