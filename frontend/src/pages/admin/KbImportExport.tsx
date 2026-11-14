import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import type { Kind } from './KbForm'

export default function KbImportExport({ kind, onImported }: { kind: Kind; onImported: () => void }) {
  const { t } = useTranslation()
  const file = useRef<HTMLInputElement>(null)
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')

  async function upload(f: File) {
    setMsg(''); setErr('')
    if (f.size > 2 * 1024 * 1024) { setErr(t('errors.file_too_large')); return }
    try {
      const r = await api<{ imported: number }>(`/api/admin/kb/${kind}/import`, { method: 'POST', body: await f.arrayBuffer(), headers: { 'Content-Type': 'text/csv' } })
      setMsg(t('adminKb.imported', { n: r.imported }))
      onImported()
    } catch (x) {
      setErr(x instanceof ApiError ? t(x.messageKey) + (x.rows.length ? ' ' + t('adminKb.badRows', { rows: x.rows.map((r) => r.row).join(', ') }) : '') : t('errors.network'))
    }
    if (file.current) file.current.value = ''
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <a href={`/api/admin/kb/${kind}/export.csv`} className="min-h-11 px-4 rounded-md font-semibold inline-flex items-center bg-white text-navy border border-slate-300 hover:bg-slate-100">{t('adminKb.export')}</a>
      <Button variant="secondary" onClick={() => file.current?.click()}>{t('adminKb.import')}</Button>
      <input ref={file} type="file" accept=".csv,text/csv" className="sr-only" aria-label={t('adminKb.import')} onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
      {msg && <span role="status" className="text-sm">{msg}</span>}
      {err && <span role="alert" className="text-sm text-brand font-semibold">{err}</span>}
    </div>
  )
}
