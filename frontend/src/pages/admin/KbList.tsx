import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../../api/client'
import VerifiedBadge from '../../components/VerifiedBadge'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import KbForm, { type Kind, type Rec } from './KbForm'
import KbImportExport from './KbImportExport'

const KINDS: Kind[] = ['rules', 'incentives', 'hs_codes']

export default function KbList() {
  const { t, i18n } = useTranslation()
  const [kind, setKind] = useState<Kind>('rules')
  const [q, setQ] = useState('')
  const [rows, setRows] = useState<Rec[] | null>(null)
  const [form, setForm] = useState<{ rec?: Rec } | null>(null)
  const [err, setErr] = useState('')
  const lang = i18n.language === 'en' ? 'en' : 'tr'

  const load = useCallback(async () => {
    try {
      setRows(await api<Rec[]>(`/api/admin/kb/${kind}?q=${encodeURIComponent(q)}`))
      setErr('')
    } catch (x) {
      setErr(t(x instanceof ApiError ? x.messageKey : 'errors.network'))
    }
  }, [kind, q, t])
  useEffect(() => { load() }, [load])

  const title = (r: Rec) => String(r[kind === 'rules' ? `title_${lang}` : kind === 'incentives' ? `name_${lang}` : `description_${lang}`] ?? '')
  const meta = (r: Rec) => kind === 'rules' ? `${r.level} · ${r.side}` : kind === 'incentives' ? String(r.provider) : String(r.sector)

  async function verify(r: Rec) {
    try { await api(`/api/admin/kb/${kind}/${encodeURIComponent(r.id)}/verify`, { method: 'POST' }); load() }
    catch (x) { setErr(t(x instanceof ApiError ? x.messageKey : 'errors.network')) }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{t('adminKb.title')}</h1>
      <p className="text-slate-700">{t('adminKb.intro')}</p>
      <div role="tablist" className="flex gap-1 overflow-x-auto">
        {KINDS.map((k) => (
          <button key={k} role="tab" aria-selected={k === kind} onClick={() => { setKind(k); setForm(null); setRows(null) }}
            className={`min-h-11 px-3 text-sm ${k === kind ? 'font-bold underline underline-offset-4 decoration-brand' : 'text-slate-700'}`}>{t(`adminKb.tabs.${k}`)}</button>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Input className="max-w-xs" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t('adminKb.search')} aria-label={t('adminKb.search')} />
        <Button onClick={() => setForm({})}>{t('adminKb.new')}</Button>
        <KbImportExport kind={kind} onImported={load} />
      </div>
      {err && <p role="alert" className="text-brand font-semibold">{err}</p>}
      {form && <KbForm key={form.rec?.id ?? 'new'} kind={kind} rec={form.rec} onDone={() => { setForm(null); load() }} onCancel={() => setForm(null)} />}
      {rows?.length === 0 && <p>{t('adminKb.empty')}</p>}
      <ul className="space-y-2">
        {rows?.map((r) => (
          <li key={r.id} className="bg-white border border-slate-200 rounded-md p-3 flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm font-bold w-16">{r.id}</span>
            <span className="flex-1 min-w-48">{title(r)} <span className="text-xs text-slate-600">({meta(r)})</span></span>
            <VerifiedBadge verified={r.verified} lastVerified={r.last_verified} />
            <Button variant="secondary" onClick={() => setForm({ rec: r })}>{t('adminKb.edit')}</Button>
            <Button variant="secondary" onClick={() => verify(r)} disabled={r.verified}>{t('adminKb.verify')}</Button>
          </li>
        ))}
      </ul>
    </div>
  )
}
