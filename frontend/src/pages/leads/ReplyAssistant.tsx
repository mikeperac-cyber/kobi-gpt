import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import Field from '../../components/ui/Field'
import Textarea from '../../components/ui/Textarea'
import type { Analysis, Message } from './types'

interface Result { inbound: Message; analysis: Analysis; draft: Message | null }

export default function ReplyAssistant({ lead, blocked, onResult, onEditDraft }: {
  lead: string
  blocked: boolean
  onResult(): void
  onEditDraft(m: Message): void
}) {
  const { t } = useTranslation()
  const [text, setText] = useState('')
  const [res, setRes] = useState<Result | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  async function analyze() {
    setBusy(true); setErr('')
    try {
      setRes(await api<Result>(`/api/leads/${lead}/reply`, { method: 'POST', json: { text } }))
      setText('')
      onResult()
    } catch (x) { setErr(x instanceof ApiError ? t(x.messageKey) : t('errors.network')) }
    setBusy(false)
  }

  const a = res?.analysis
  const terms = a?.terms
  return (
    <Card className="space-y-4">
      <h2 className="text-lg font-semibold">{t('leads.reply.title')}</h2>
      {blocked && !res ? <p className="text-slate-700">{t('leads.detail.blocked')}</p> : (
        <>
          <Field label={t('leads.reply.label')}><Textarea rows={6} value={text} maxLength={10000} onChange={(e) => setText(e.target.value)} /></Field>
          <Button onClick={analyze} disabled={busy || !text.trim()}>{busy ? t('leads.reply.analyzing') : t('leads.reply.analyze')}</Button>
        </>
      )}
      {err && <p role="alert" className="text-brand font-semibold">{err}</p>}
      {a && (
        <div className="space-y-3" aria-live="polite">
          {a.red_flags.length > 0 && (
            <div role="alert" className="space-y-2">
              <h3 className="font-semibold">{t('leads.reply.flagsTitle')}</h3>
              <ul className="space-y-2">
                {a.red_flags.map((f) => (
                  <li key={f} className="bg-amber-50 border border-amber-400 rounded-md p-3">
                    <p className="text-sm"><span aria-hidden="true">⚠ </span>{t(`leads.reply.flags.${f}`)}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {a.summary.length === 0 && <p className="text-slate-700">{t('leads.reply.noAnalysis')}</p>}
          {a.translation && (
            <div><h3 className="font-semibold">{t('leads.reply.translation')}</h3><p className="whitespace-pre-wrap bg-slate-50 rounded-md p-3">{a.translation}</p></div>
          )}
          {a.summary.length > 0 && (
            <div><h3 className="font-semibold">{t('leads.reply.summary')}</h3><ul className="list-disc pl-5">{a.summary.map((s, i) => <li key={i}>{s}</li>)}</ul></div>
          )}
          {a.summary.length > 0 && (
            <p><span className="font-semibold">{t('leads.reply.intent')}: </span>{t(`leads.reply.intents.${a.intent}`)}</p>
          )}
          {terms && a.summary.length > 0 && (
            <div>
              <h3 className="font-semibold">{t('leads.reply.terms')}</h3>
              <dl className="grid grid-cols-[auto_1fr] gap-x-3 text-sm">
                <dt>{t('leads.reply.quantity')}</dt><dd>{terms.quantity ?? t('leads.reply.none')}</dd>
                <dt>{t('leads.reply.incoterm')}</dt><dd>{terms.incoterm ?? t('leads.reply.none')}</dd>
                <dt>{t('leads.reply.delivery_date')}</dt><dd>{terms.delivery_date ?? t('leads.reply.none')}</dd>
                <dt>{t('leads.reply.certifications')}</dt><dd>{terms.certifications.length ? terms.certifications.join(', ') : t('leads.reply.none')}</dd>
              </dl>
            </div>
          )}
          {a.opt_out ? (
            <div role="status" className="bg-slate-100 rounded-md p-3 space-y-1">
              <p className="font-semibold">{t('leads.reply.optOut')}</p>
              {a.opt_out_source === 'keyword' && <p className="text-sm">{t('leads.reply.optOutKeyword')}</p>}
            </div>
          ) : res.draft && (
            <div role="status" className="space-y-2">
              <p className="font-semibold">{t('leads.reply.suggested')}</p>
              <div className="flex flex-wrap gap-2">
                <Button variant="secondary" onClick={() => onEditDraft(res.draft!)}>{t('leads.reply.editDraft')}</Button>
                <Link to="/approvals" className="min-h-11 inline-flex items-center px-4 rounded-md font-semibold bg-navy text-white">{t('leads.reply.toApprovals')}</Link>
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  )
}
