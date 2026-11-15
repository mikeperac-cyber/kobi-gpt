import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import Field from '../../components/ui/Field'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import { SourceNoteField } from './LeadForm'

interface Preview { file_id: string; headers: string[]; rows: string[][]; total: number }
interface Result { imported: number; skipped: number; errors: { row: number; reason: string }[] }
const FIELDS = ['company_name', 'country', 'contact_name', 'email', 'website', 'notes'] as const
// Header names we can guess a mapping for (TR + EN); the user can always change it.
const GUESS: Record<string, RegExp> = {
  company_name: /firma|company|şirket|sirket|^name/i, country: /ülke|ulke|country/i, contact_name: /kişi|kisi|contact/i,
  email: /mail|posta/i, website: /web|site|url/i, notes: /not|note/i,
}

export default function CsvImport({ onDone, onCancel }: { onDone(): void; onCancel(): void }) {
  const { t } = useTranslation()
  const [pv, setPv] = useState<Preview | null>(null)
  const [map, setMap] = useState<Record<string, string>>({})
  const [note, setNote] = useState('')
  const [res, setRes] = useState<Result | null>(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  async function pick(f: File) {
    setErr(''); setRes(null)
    if (f.size > 2 * 1024 * 1024) { setErr(t('errors.file_too_large')); return }
    const fd = new FormData()
    fd.append('file', f)
    try {
      const p = await api<Preview>('/api/leads/import/preview', { method: 'POST', body: fd })
      setPv(p)
      const g: Record<string, string> = {}
      for (const k of FIELDS) {
        const h = p.headers.find((x) => GUESS[k].test(x) && !Object.values(g).includes(x))
        if (h) g[k] = h
      }
      setMap(g)
    } catch (x) { setErr(x instanceof ApiError ? t(x.messageKey) : t('errors.network')) }
  }

  async function run(e: FormEvent) {
    e.preventDefault()
    if (!pv) return
    setErr(''); setBusy(true)
    try {
      const mapping = Object.fromEntries(Object.entries(map).filter(([, v]) => v))
      setRes(await api<Result>('/api/leads/import', { method: 'POST', json: { file_id: pv.file_id, mapping, source_note: note } }))
      setPv(null)
      onDone()
    } catch (x) { setErr(x instanceof ApiError ? t(x.messageKey) : t('errors.network')) }
    setBusy(false)
  }

  return (
    <Card className="space-y-4">
      <h2 className="text-lg font-semibold">{t('leads.csv.title')}</h2>
      {!pv && !res && (
        <Field label={t('leads.csv.file')}><Input type="file" accept=".csv,text/csv" onChange={(e) => e.target.files?.[0] && pick(e.target.files[0])} /></Field>
      )}
      {pv && (
        <form onSubmit={run} className="space-y-4">
          <div>
            <h3 className="font-semibold mb-1">{t('leads.csv.previewTitle', { n: pv.total })}</h3>
            <div className="overflow-x-auto border border-slate-200 rounded-md">
              <table className="text-sm w-full">
                <thead><tr>{pv.headers.map((h) => <th key={h} className="text-left px-2 py-1 bg-slate-50 whitespace-nowrap">{h}</th>)}</tr></thead>
                <tbody>{pv.rows.map((r, i) => <tr key={i} className="border-t border-slate-100">{r.map((c, j) => <td key={j} className="px-2 py-1 whitespace-nowrap">{c}</td>)}</tr>)}</tbody>
              </table>
            </div>
          </div>
          <div>
            <h3 className="font-semibold mb-2">{t('leads.csv.mapTitle')}</h3>
            <div className="grid sm:grid-cols-2 gap-3">
              {FIELDS.map((k) => (
                <Field key={k} label={t(`leads.csv.${k}`)}>
                  <Select value={map[k] ?? ''} onChange={(e) => setMap({ ...map, [k]: e.target.value })}>
                    <option value="">{t('leads.csv.none')}</option>
                    {pv.headers.map((h) => <option key={h} value={h}>{h}</option>)}
                  </Select>
                </Field>
              ))}
            </div>
          </div>
          <SourceNoteField value={note} onChange={setNote} />
          {err && <p role="alert" className="text-brand font-semibold">{err}</p>}
          <div className="flex gap-2">
            <Button type="submit" disabled={busy || !map.company_name}>{t('leads.csv.run')}</Button>
            <Button type="button" variant="secondary" onClick={onCancel}>{t('common.cancel')}</Button>
          </div>
        </form>
      )}
      {!pv && err && <p role="alert" className="text-brand font-semibold">{err}</p>}
      {res && (
        <div role="status" className="space-y-2">
          <p className="font-semibold">{t('leads.csv.result', { imported: res.imported, skipped: res.skipped })}</p>
          {res.errors.length > 0 && (
            <>
              <h3 className="font-semibold">{t('leads.csv.errorsTitle')}</h3>
              <ul className="list-disc pl-5 text-sm">
                {res.errors.map((x) => <li key={x.row}>{t('leads.csv.row', { row: x.row })}: {t(`leads.csv.reasons.${x.reason}`)}</li>)}
              </ul>
            </>
          )}
        </div>
      )}
      {!pv && <Button variant="secondary" onClick={onCancel}>{res ? t('common.close') : t('common.cancel')}</Button>}
    </Card>
  )
}
