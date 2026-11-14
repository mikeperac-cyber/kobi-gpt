import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { COUNTRIES, STR, countryName } from './strings'
import type { Lang } from './types'

export default function RfqForm({ slug, lang, productNames }: { slug: string; lang: Lang; productNames: string[] }) {
  const s = STR[lang].rfq
  const [state, setState] = useState<'idle' | 'sending' | 'done' | 'invalid' | 'limit' | 'error'>('idle')
  const [picked, setPicked] = useState<string[]>([])

  if (state === 'done') {
    return <div role="status"><h3 className="text-xl font-semibold">{s.thanksTitle}</h3><p>{s.thanks}</p></div>
  }

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const f = new FormData(e.currentTarget)
    const v = (k: string) => String(f.get(k) ?? '').trim()
    setState('sending')
    try {
      await api(`/api/public/storefronts/${encodeURIComponent(slug)}/rfq`, {
        method: 'POST',
        json: {
          company_name: v('company_name'), contact_name: v('contact_name'), email: v('email'), country: v('country'),
          products: picked, quantity: v('quantity'), message: v('message'),
          gdpr_consent: f.get('gdpr_consent') === 'on', website_hp: v('website_hp'),
        },
      })
      setState('done')
    } catch (err) {
      const st = err instanceof ApiError ? err.status : 0
      setState(st === 422 ? 'invalid' : st === 429 ? 'limit' : 'error')
    }
  }

  const input = 'w-full rounded-md border bg-white text-slate-900 px-3 py-2 min-h-11 border-slate-500'
  const label = 'block text-sm font-semibold mb-1'
  return (
    <form onSubmit={submit} className="relative grid gap-4 sm:grid-cols-2">
      <div><label className={label} htmlFor="rq-co">{s.company} *</label><input id="rq-co" name="company_name" required maxLength={120} autoComplete="organization" className={input} /></div>
      <div><label className={label} htmlFor="rq-ct">{s.contact} *</label><input id="rq-ct" name="contact_name" required maxLength={120} autoComplete="name" className={input} /></div>
      <div><label className={label} htmlFor="rq-em">{s.email} *</label><input id="rq-em" name="email" type="email" required maxLength={254} autoComplete="email" className={input} /></div>
      <div>
        <label className={label} htmlFor="rq-cn">{s.country} *</label>
        <select id="rq-cn" name="country" required defaultValue="" className={input}>
          <option value="" disabled>{s.select}</option>
          {COUNTRIES.map((c) => <option key={c} value={c}>{countryName(c, lang)}</option>)}
        </select>
      </div>
      {productNames.length > 0 && (
        <fieldset className="sm:col-span-2">
          <legend className={label}>{s.products}</legend>
          <div className="flex flex-wrap gap-x-5">
            {productNames.map((n) => (
              <label key={n} className="flex items-center gap-2 min-h-11">
                <input type="checkbox" className="h-5 w-5" checked={picked.includes(n)}
                  onChange={(e) => setPicked(e.target.checked ? [...picked, n] : picked.filter((x) => x !== n))} />
                {n}
              </label>
            ))}
          </div>
        </fieldset>
      )}
      <div className="sm:col-span-2"><label className={label} htmlFor="rq-qt">{s.quantity}</label><input id="rq-qt" name="quantity" maxLength={120} className={input} /></div>
      <div className="sm:col-span-2"><label className={label} htmlFor="rq-ms">{s.message} *</label><textarea id="rq-ms" name="message" required rows={4} maxLength={2000} className={input} /></div>
      <div aria-hidden="true" className="absolute -left-[9999px] h-0 w-0 overflow-hidden">
        <input name="website_hp" tabIndex={-1} autoComplete="off" />
      </div>
      <label className="sm:col-span-2 flex items-start gap-3 text-sm">
        <input type="checkbox" name="gdpr_consent" required className="h-5 w-5 mt-0.5 shrink-0" />
        <span>{s.consent} <Link to={`/s/${slug}/datenschutz?lang=${lang}`} className="underline" target="_blank">{s.consentLink}</Link> *</span>
      </label>
      {state !== 'idle' && state !== 'sending' && (
        <p role="alert" className="sm:col-span-2 text-red-700 font-semibold">{state === 'invalid' ? s.invalid : state === 'limit' ? s.tooMany : s.error}</p>
      )}
      <div className="sm:col-span-2">
        <button type="submit" disabled={state === 'sending'} className="rounded-md px-6 py-3 min-h-11 font-semibold bg-slate-900 text-white hover:bg-slate-700 disabled:opacity-60">
          {state === 'sending' ? s.sending : s.submit}
        </button>
      </div>
    </form>
  )
}
