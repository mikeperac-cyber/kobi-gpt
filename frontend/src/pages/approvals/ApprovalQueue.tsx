import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../../api/client'
import DemoBadge from '../../components/DemoBadge'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import Modal from '../../components/ui/Modal'
import Textarea from '../../components/ui/Textarea'
import { buyerLang, quoteCover } from '../../data/buyerStrings'
import { formatDate, formatMoney, formatNumber } from '../../i18n/format'
import type { Message } from '../leads/types'
import type { Quote } from '../quotes/types'

type LeadSum = { company_name?: string; email?: string; contact_name?: string; country?: string; is_demo?: boolean }
type Msg = Message & { lead: LeadSum }
type Q = Quote & { lead: LeadSum }
type Item = { kind: 'message'; at: string; m: Msg } | { kind: 'quote'; at: string; q: Q }

const MAILTO_MAX = 1800

async function copyText(text: string) {
  try { await navigator.clipboard.writeText(text); return }
  catch { /* fall through to the textarea route */ }
  const ta = document.createElement('textarea')
  ta.value = text
  document.body.appendChild(ta)
  ta.select()
  document.execCommand('copy')
  ta.remove()
}

/** mailto cannot be long or empty-addressed: those go to the clipboard instead. */
async function handOff(email: string | undefined, subject: string, body: string): Promise<'mailto' | 'clipboard'> {
  const url = `mailto:${email ?? ''}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
  if (!email || url.length > MAILTO_MAX) {
    await copyText(`Subject: ${subject}\n\n${body}`)
    return 'clipboard'
  }
  const a = document.createElement('a')
  a.href = url
  document.body.appendChild(a)
  a.click()
  a.remove()
  return 'mailto'
}

async function downloadPdf(id: string) {
  const res = await fetch(`/api/quotes/${id}/pdf`, { credentials: 'include' })
  if (!res.ok) throw new Error('pdf')
  const url = URL.createObjectURL(await res.blob())
  const a = document.createElement('a')
  a.href = url
  a.download = `quote-${id}.pdf`
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 10000)
}

export default function ApprovalQueue() {
  const { t } = useTranslation()
  const [items, setItems] = useState<Item[] | null>(null)
  const [busy, setBusy] = useState('')
  const [toast, setToast] = useState<string[]>([])
  const [err, setErr] = useState('')
  const [rejecting, setRejecting] = useState<Item | null>(null)
  const [reason, setReason] = useState('')
  const [rejErr, setRejErr] = useState('')

  const load = useCallback(async () => {
    try {
      const r = await api<{ messages: Msg[]; quotes: Q[] }>('/api/approvals')
      const all: Item[] = [...r.messages.map((m) => ({ kind: 'message' as const, at: m.created_at, m })), ...r.quotes.map((q) => ({ kind: 'quote' as const, at: q.created_at, q }))]
      all.sort((a, b) => b.at.localeCompare(a.at))
      setItems(all)
    } catch (x) { setErr(x instanceof ApiError ? t(x.messageKey) : t('approvals.loadError')) }
  }, [t])
  useEffect(() => { void load() }, [load])
  useEffect(() => { if (toast.length) { const h = setTimeout(() => setToast([]), 8000); return () => clearTimeout(h) } }, [toast])

  const idOf = (i: Item) => (i.kind === 'message' ? i.m.id : i.q.id)
  const remove = (i: Item) => setItems((cur) => cur && cur.filter((x) => idOf(x) !== idOf(i)))

  async function approve(i: Item) {
    setBusy(idOf(i)); setErr(''); setToast([])
    try {
      if (i.kind === 'message') {
        const m = await api<Message>(`/api/messages/${i.m.id}/approve`, { method: 'POST' })
        const how = await handOff(i.m.lead.email, m.subject ?? i.m.subject ?? '', m.body ?? i.m.body)
        remove(i)
        setToast([t(how === 'mailto' ? 'approvals.handed' : 'approvals.copied')])
      } else {
        const q = i.q
        await api(`/api/quotes/${q.id}/approve`, { method: 'POST' })
        remove(i)
        const lang = buyerLang(q.lead.country ?? '')
        const msgs: string[] = []
        try { await downloadPdf(q.id) } catch { msgs.push(t('approvals.downloadFail')) }
        const cover = quoteCover[lang]
        const how = await handOff(q.lead.email, cover.subject, cover.body(q.lead.contact_name ?? ''))
        setToast([t(how === 'mailto' ? 'approvals.handed' : 'approvals.copied'), t('approvals.attachPdf'), ...msgs])
      }
    } catch (x) { setErr(x instanceof ApiError ? t(x.messageKey) : t('errors.network')); void load() }
    setBusy('')
  }

  async function reject() {
    if (!rejecting) return
    if (!reason.trim()) return setRejErr(t('errors.validation_error'))
    const i = rejecting
    setBusy(idOf(i)); setRejErr('')
    try {
      await api(`/api/${i.kind === 'message' ? 'messages' : 'quotes'}/${idOf(i)}/reject`, { method: 'POST', json: { reason: reason.trim() } })
      remove(i); setRejecting(null); setReason('')
    } catch (x) { setRejErr(x instanceof ApiError ? t(x.messageKey) : t('errors.network')) }
    setBusy('')
  }

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">{t('approvals.title')}</h1>
      <p className="text-slate-700">{t('approvals.intro')}</p>
      {toast.length > 0 && (
        <div role="status" className="bg-green-50 border border-green-600 rounded-md p-3 font-semibold space-y-1">
          {toast.map((m) => <p key={m}>{m}</p>)}
        </div>
      )}
      {err && <p role="alert" className="text-brand font-semibold">{err}</p>}
      {items === null && !err && <p role="status">{t('common.loading')}</p>}
      {items?.length === 0 && <p className="text-slate-700">{t('approvals.empty')}</p>}
      <ul className="space-y-3">
        {items?.map((i) => {
          const lead = i.kind === 'message' ? i.m.lead : i.q.lead
          const id = idOf(i)
          return (
            <li key={id}>
              <Card className="space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="font-semibold text-lg">{lead.company_name}</h2>
                  {lead.is_demo && <DemoBadge />}
                  <Badge>{t(i.kind === 'quote' ? 'approvals.kind.quote' : `approvals.kind.${i.m.kind}`, { defaultValue: i.kind })}</Badge>
                </div>
                <p className="text-sm text-slate-700">
                  {i.kind === 'message' && <>{t('approvals.lang')}: {i.m.language.toUpperCase()} · </>}
                  {t('approvals.createdAt')}: {formatDate(i.at)}
                </p>
                {i.kind === 'message' ? (
                  <>
                    {i.m.subject && <p className="font-semibold">{i.m.subject}</p>}
                    <p className="whitespace-pre-wrap text-sm line-clamp-4">{i.m.body}</p>
                  </>
                ) : (
                  <>
                    <p>{t('approvals.quoteSummary', { qty: `${formatNumber(i.q.quantity)} ${i.q.unit}`, incoterm: i.q.incoterm, total: formatMoney(i.q.total, i.q.currency) })}</p>
                    <p className="text-sm text-slate-700">{t('approvals.quoteReadOnly')}</p>
                  </>
                )}
                <div className="flex flex-wrap gap-2 pt-1">
                  <Button onClick={() => approve(i)} disabled={busy === id}>{busy === id ? t('approvals.working') : t('approvals.approve')}</Button>
                  {i.kind === 'message' && <Link to={`/leads/${i.m.lead_id}?draft=${id}`} className="min-h-11 inline-flex items-center px-4 rounded-md font-semibold border border-slate-300 bg-white">{t('approvals.edit')}</Link>}
                  <Button variant="secondary" onClick={() => { setRejecting(i); setReason(''); setRejErr('') }}>{t('approvals.reject')}</Button>
                </div>
              </Card>
            </li>
          )
        })}
      </ul>
      {rejecting && (
        <Modal title={t('approvals.rejectTitle')} onClose={() => setRejecting(null)}>
          <label htmlFor="rej" className="block text-sm font-semibold mb-1">{t('approvals.rejectReason')}</label>
          <Textarea id="rej" rows={3} maxLength={300} value={reason} onChange={(e) => setReason(e.target.value)} />
          {rejErr && <p role="alert" className="text-brand font-semibold mt-1">{rejErr}</p>}
          <div className="flex gap-2 mt-4">
            <Button onClick={reject} disabled={busy === idOf(rejecting)}>{t('approvals.rejectConfirm')}</Button>
            <Button variant="secondary" onClick={() => setRejecting(null)}>{t('common.cancel')}</Button>
          </div>
        </Modal>
      )}
    </section>
  )
}
