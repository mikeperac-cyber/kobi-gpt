import { useCallback, useEffect, useRef, useState } from 'react'
import { PageSkeleton } from '../../components/ui/Skeleton'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import Modal from '../../components/ui/Modal'
import DemoBadge from '../../components/DemoBadge'
import { formatDate } from '../../i18n/format'
import OutreachDraft from './OutreachDraft'
import ReplyAssistant from './ReplyAssistant'
import SampleTask from './SampleTask'
import ScoreBreakdown from './ScoreBreakdown'
import type { Lead, Message } from './types'

export default function LeadDetail() {
  const { t } = useTranslation()
  const { id = '' } = useParams()
  const [lead, setLead] = useState<Lead | null>(null)
  const [msgs, setMsgs] = useState<Message[]>([])
  const [draft, setDraft] = useState<Message | null>(null)
  const [confirm, setConfirm] = useState<'won' | 'lost' | 'do_not_contact' | null>(null)
  const [busy, setBusy] = useState(false)
  const [sample, setSample] = useState(false)
  const [params] = useSearchParams()
  const [err, setErr] = useState('')
  const draftRef = useRef<HTMLDivElement>(null)
  const opened = useRef(false)

  const load = useCallback(async () => {
    try {
      const [l, m] = await Promise.all([api<Lead>(`/api/leads/${id}`), api<Message[]>(`/api/leads/${id}/messages`)])
      setLead(l); setMsgs(m)
    } catch (x) { setErr(x instanceof ApiError ? t(x.messageKey) : t('errors.network')) }
  }, [id, t])
  useEffect(() => { void load() }, [load])
  useEffect(() => { // ?draft=<id> comes from the approval queue's Edit button
    const want = params.get('draft')
    const m = want ? msgs.find((x) => x.id === want && x.status === 'draft') : undefined
    if (m && !opened.current) { opened.current = true; setDraft(m) }
  }, [msgs, params])
  useEffect(() => { if (draft) draftRef.current?.scrollIntoView({ block: 'nearest' }) }, [draft?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  async function prepare() {
    setBusy(true); setErr('')
    try { setDraft(await api<Message>(`/api/leads/${id}/draft`, { method: 'POST', json: { tone: [] } })); await load() }
    catch (x) { setErr(x instanceof ApiError ? t(x.messageKey) : t('errors.network')) }
    setBusy(false)
  }

  async function setStatus(s: string) {
    setConfirm(null); setErr('')
    try { await api(`/api/leads/${id}`, { method: 'PATCH', json: { status: s } }); await load() }
    catch (x) { setErr(x instanceof ApiError ? t(x.messageKey) : t('errors.network')) }
  }

  if (!lead) return <PageSkeleton error={err} />
  const blocked = lead.status === 'do_not_contact'
  const closed = blocked || lead.status === 'won' || lead.status === 'lost'

  return (
    <section className="space-y-4">
      <Link to="/leads" className="underline min-h-11 inline-flex items-center">← {t('leads.detail.back')}</Link>
      <Card className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-semibold">{lead.company_name}</h1>
          {lead.is_demo && <DemoBadge />}
        </div>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
          <dt className="font-semibold">{t('leads.colCountry')}</dt><dd>{lead.country}</dd>
          <dt className="font-semibold">{t('leads.detail.contact')}</dt><dd>{[lead.contact_name, lead.email].filter(Boolean).join(' · ') || '—'}</dd>
          {lead.website && <><dt className="font-semibold">{t('leads.detail.website')}</dt><dd>{lead.website}</dd></>}
          <dt className="font-semibold">{t('leads.colStatus')}</dt><dd>{t(`leads.status.${lead.status}`)}</dd>
          <dt className="font-semibold">{t('leads.colScore')}</dt><dd><ScoreBreakdown score={lead.score} breakdown={lead.score_breakdown} /></dd>
          <dt className="font-semibold">{t('leads.detail.sourceNote')}</dt><dd>{lead.source_note}</dd>
          <dt className="font-semibold">{t('leads.colCreated')}</dt><dd>{formatDate(lead.created_at)}</dd>
          {lead.products_of_interest && lead.products_of_interest.length > 0 && <><dt className="font-semibold">{t('leads.detail.products')}</dt><dd>{lead.products_of_interest.join(', ')}</dd></>}
          {lead.quantity ? <><dt className="font-semibold">{t('leads.detail.quantity')}</dt><dd>{String(lead.quantity)}</dd></> : null}
        </dl>
        {lead.notes && (
          <div>
            <h2 className="font-semibold text-sm">{lead.source === 'rfq' ? t('leads.detail.rfqMessage') : t('leads.detail.notes')}</h2>
            <p className="whitespace-pre-wrap bg-slate-50 rounded-md p-3">{lead.notes}</p>
          </div>
        )}
        <div className="flex flex-wrap gap-2">
          <Button onClick={prepare} disabled={busy || blocked} aria-describedby={blocked ? 'dnc-note' : undefined}>{busy ? t('leads.detail.preparing') : t('leads.detail.prepare')}</Button>
          {!blocked && <Link to={`/leads/${id}/quote`} className="min-h-11 inline-flex items-center px-4 rounded-md font-semibold border border-slate-300 bg-white">{t('leads.detail.prepareQuote')}</Link>}
          {!blocked && <Button variant="secondary" onClick={() => setSample(true)}>{t('leads.detail.sample')}</Button>}
          {!closed && <Button variant="secondary" onClick={() => setConfirm('won')}>{t('leads.detail.markWon')}</Button>}
          {!closed && <Button variant="secondary" onClick={() => setConfirm('lost')}>{t('leads.detail.markLost')}</Button>}
          {!blocked && <Button variant="secondary" onClick={() => setConfirm('do_not_contact')}>{t('leads.detail.markDnc')}</Button>}
        </div>
        {blocked && <p id="dnc-note" className="text-sm text-slate-700">{t('leads.detail.blocked')}</p>}
        {err && <p role="alert" className="text-brand font-semibold">{err}</p>}
      </Card>

      <div ref={draftRef}>
        {draft && <OutreachDraft lead={id} message={draft} onChange={(m) => { setDraft(m); void load() }} onReplace={(m) => { setDraft(m); void load() }} onClose={(e) => { setDraft(null); void load().then(() => e && setErr(e)) }} />}
      </div>

      {sample && <SampleTask lead={id} onClose={() => setSample(false)} />}

      <ReplyAssistant lead={id} blocked={blocked} onResult={load} onEditDraft={setDraft} />

      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">{t('leads.detail.history')}</h2>
        {msgs.length === 0 && <p className="text-slate-700">{t('leads.detail.noHistory')}</p>}
        <ul className="space-y-2">
          {msgs.map((m) => (
            <li key={m.id} className="border border-slate-200 rounded-md p-3 space-y-1">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="font-semibold">{m.direction === 'inbound' ? t('leads.detail.inbound') : t('leads.detail.outbound')}</span>
                <span>{t(`leads.detail.msgStatus.${m.status}`, { defaultValue: m.status })}</span>
                <span className="text-slate-600">{formatDate(m.created_at)}</span>
              </div>
              {m.subject && <p className="font-semibold">{m.subject}</p>}
              <p className="whitespace-pre-wrap text-sm line-clamp-4">{m.body}</p>
              {m.status === 'draft' && m.direction === 'outbound' && <Button variant="secondary" onClick={() => setDraft(m)}>{t('leads.detail.openDraft')}</Button>}
            </li>
          ))}
        </ul>
      </Card>

      {confirm && (
        <Modal title={t('leads.detail.confirmTitle')} onClose={() => setConfirm(null)}>
          <p>{t('leads.detail.confirmBody', { status: t(`leads.status.${confirm}`) })}</p>
          {confirm === 'do_not_contact' && <p className="font-semibold mt-2">{t('leads.detail.dncWarn')}</p>}
          <div className="flex gap-2 mt-4">
            <Button onClick={() => setStatus(confirm)}>{t('leads.detail.confirm')}</Button>
            <Button variant="secondary" onClick={() => setConfirm(null)}>{t('common.cancel')}</Button>
          </div>
        </Modal>
      )}
    </section>
  )
}
