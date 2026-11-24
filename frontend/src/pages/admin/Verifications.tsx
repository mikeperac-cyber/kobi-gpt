import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import Modal from '../../components/ui/Modal'
import { PageSkeleton } from '../../components/ui/Skeleton'
import Textarea from '../../components/ui/Textarea'
import { formatDate } from '../../i18n/format'

type Status = 'pending' | 'verified' | 'rejected'
type Item = {
  id: string; company_name: string | null; kind: 'tax_plate' | 'certificate'; name: string; issuer: string
  valid_until: string | null; created_at: string; reject_reason: string | null
}
const TABS: Status[] = ['pending', 'verified', 'rejected']

/** Admin queue: open each private document, then verify or reject it with a reason. */
export default function Verifications() {
  const { t } = useTranslation()
  const [tab, setTab] = useState<Status>('pending')
  const [items, setItems] = useState<Item[] | null>(null)
  const [err, setErr] = useState('')
  const [rejecting, setRejecting] = useState<Item | null>(null)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState('')
  const load = useCallback(() => {
    api<Item[]>(`/api/admin/verifications?status=${tab}`).then(setItems)
      .catch((x) => setErr(t(x instanceof ApiError ? x.messageKey : 'errors.network')))
  }, [tab, t])
  useEffect(() => { load() }, [load])

  const decide = async (it: Item, action: 'verify' | 'reject', body?: object) => {
    setBusy(it.id); setErr('')
    try {
      await api(`/api/admin/verifications/${it.id}/${action}`, { method: 'POST', json: body })
      setRejecting(null); setReason(''); load()
    } catch (x) { setErr(t(x instanceof ApiError ? x.messageKey : 'errors.network')) } finally { setBusy('') }
  }

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">{t('adminVerify.title')}</h1>
      <div role="tablist" className="flex gap-2">
        {TABS.map((k) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => { if (k !== tab) { setItems(null); setTab(k) } }}
            className={`min-h-11 px-4 rounded-md font-semibold border ${tab === k ? 'bg-navy text-white border-navy' : 'bg-white border-slate-300'}`}>
            {t(`adminVerify.tab.${k}`)}
          </button>
        ))}
      </div>
      {err && <p role="alert" className="text-brand font-semibold">{err}</p>}
      {!items ? <PageSkeleton /> : items.length === 0 ? <p className="text-slate-600">{t('adminVerify.empty')}</p> : (
        <ul className="space-y-3">
          {items.map((it) => (
            <li key={it.id}><Card className="space-y-2">
              <p className="font-semibold">{it.company_name} — {it.kind === 'tax_plate' ? t('verify.taxPlate') : it.name}</p>
              <p className="text-sm text-slate-700">
                {[it.issuer, it.valid_until && t('verify.validUntil', { date: formatDate(it.valid_until) }),
                  t('adminVerify.submitted', { date: formatDate(it.created_at) })].filter(Boolean).join(' · ')}
              </p>
              {it.reject_reason && <p className="text-sm text-brand">{it.reject_reason}</p>}
              <div className="flex flex-wrap gap-2">
                <a href={`/api/admin/verifications/${it.id}/file`} target="_blank" rel="noopener noreferrer"
                  className="inline-flex min-h-11 items-center px-4 rounded-md border border-slate-300 bg-white font-semibold">{t('adminVerify.open')}</a>
                {tab === 'pending' && <>
                  <Button disabled={busy === it.id} onClick={() => void decide(it, 'verify')}>{t('adminVerify.verify')}</Button>
                  <Button variant="secondary" disabled={busy === it.id} onClick={() => setRejecting(it)}>{t('adminVerify.reject')}</Button>
                </>}
              </div>
            </Card></li>
          ))}
        </ul>
      )}
      {rejecting && (
        <Modal title={t('adminVerify.reject')} onClose={() => setRejecting(null)}>
          <label className="block text-sm font-semibold">{t('adminVerify.reason')}
            <Textarea className="mt-1" value={reason} maxLength={300} onChange={(e) => setReason(e.target.value)} />
          </label>
          <div className="flex gap-2 mt-4">
            <Button disabled={!reason.trim() || busy === rejecting.id} onClick={() => void decide(rejecting, 'reject', { reason })}>{t('adminVerify.reject')}</Button>
            <Button variant="secondary" onClick={() => setRejecting(null)}>{t('common.cancel')}</Button>
          </div>
        </Modal>
      )}
    </section>
  )
}
