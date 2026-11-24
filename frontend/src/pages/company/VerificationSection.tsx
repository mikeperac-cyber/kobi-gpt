import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../../api/client'
import Card from '../../components/ui/Card'
import Input from '../../components/ui/Input'
import { formatDate } from '../../i18n/format'

type Verification = {
  id: string; kind: 'tax_plate' | 'certificate'; name: string; status: 'pending' | 'verified' | 'rejected'
  valid_until: string | null; reject_reason: string | null; reviewed_at: string | null
}
type Row = { kind: Verification['kind']; name: string }

const fold = (x: string) => x.toLocaleLowerCase('tr').trim()

/** Producer side of supplier verification: upload a private document per row; buyers only see the outcome. */
export default function VerificationSection({ certifications }: { certifications: string[] }) {
  const { t } = useTranslation()
  const [items, setItems] = useState<Verification[] | null>(null)
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState<Record<string, string>>({})
  const [until, setUntil] = useState<Record<string, string>>({})
  const load = useCallback(() => { api<Verification[]>('/api/verifications').then(setItems).catch(() => setItems([])) }, [])
  useEffect(() => { load() }, [load])

  const rows: Row[] = [{ kind: 'tax_plate', name: 'tax_plate' }, ...certifications.map((name) => ({ kind: 'certificate' as const, name }))]
  const latest = (r: Row) => items?.find((v) => v.kind === r.kind && fold(v.name) === fold(r.name)) // newest first

  const upload = async (r: Row, file: File) => {
    setBusy(r.name); setErr((e) => ({ ...e, [r.name]: '' }))
    try {
      const body = new FormData()
      body.append('file', file)
      const { url } = await api<{ url: string }>('/api/uploads/document', { method: 'POST', body })
      await api('/api/verifications', { method: 'POST', json: {
        kind: r.kind, name: r.kind === 'certificate' ? r.name : '', file_url: url, valid_until: until[r.name] || null } })
      load()
    } catch (x) {
      setErr((e) => ({ ...e, [r.name]: t(x instanceof ApiError ? x.messageKey : 'errors.network') }))
    } finally { setBusy('') }
  }

  const status = (v?: Verification) => {
    if (!v) return <span className="text-slate-600">{t('verify.status.none')}</span>
    if (v.status === 'verified') return <span className="text-green-800 font-semibold">{t('verify.status.verified', { date: formatDate(v.reviewed_at!) })}{v.valid_until && ` · ${t('verify.validUntil', { date: formatDate(v.valid_until) })}`}</span>
    if (v.status === 'rejected') return <span className="text-brand font-semibold">{t('verify.status.rejected', { reason: v.reject_reason })}</span>
    return <span className="text-amber-800 font-semibold">{t('verify.status.pending')}</span>
  }

  return (
    <Card className="max-w-2xl mx-auto mt-6 space-y-4">
      <h2 className="text-xl font-semibold">{t('verify.title')}</h2>
      <p className="text-sm text-slate-700">{t('verify.intro')}</p>
      <ul className="divide-y divide-slate-200">
        {rows.map((r) => (
          <li key={`${r.kind}-${r.name}`} className="py-3 space-y-2">
            <div className="flex flex-wrap justify-between gap-2">
              <span className="font-semibold">{r.kind === 'tax_plate' ? t('verify.taxPlate') : r.name}</span>
              <span className="text-sm" aria-live="polite">{items ? status(latest(r)) : ''}</span>
            </div>
            <div className="flex flex-wrap items-end gap-3">
              {r.kind === 'certificate' && (
                <label className="text-sm">{t('verify.validUntilLabel')}
                  <Input type="date" className="mt-1" value={until[r.name] ?? ''} onChange={(e) => setUntil((u) => ({ ...u, [r.name]: e.target.value }))} />
                </label>
              )}
              <label className={`inline-flex min-h-11 items-center px-4 rounded-md border border-slate-300 bg-white font-semibold cursor-pointer ${busy ? 'opacity-60 pointer-events-none' : ''}`}>
                {busy === r.name ? t('verify.uploading') : t('verify.upload')}
                <input type="file" className="sr-only" accept=".pdf,image/jpeg,image/png,image/webp" disabled={!!busy}
                  onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ''; if (f) void upload(r, f) }} />
              </label>
            </div>
            {err[r.name] && <p role="alert" className="text-sm text-brand font-semibold">{err[r.name]}</p>}
          </li>
        ))}
      </ul>
      {certifications.length === 0 && <p className="text-sm text-slate-600">{t('verify.noCerts')}</p>}
    </Card>
  )
}
