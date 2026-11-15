import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import Field from '../../components/ui/Field'
import Input from '../../components/ui/Input'
import Textarea from '../../components/ui/Textarea'
import type { Message } from './types'

const TONES = ['formal', 'shorter', 'samples'] as const

export default function OutreachDraft({ lead, message, onChange, onReplace, onClose }: {
  lead: string
  message: Message
  onChange(m: Message): void
  onReplace(m: Message): void
  onClose(err?: string): void
}) {
  const { t, i18n } = useTranslation()
  const [subject, setSubject] = useState(message.subject ?? '')
  const [body, setBody] = useState(message.body)
  const [tones, setTones] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')
  useEffect(() => { setSubject(message.subject ?? ''); setBody(message.body); setMsg(''); setErr('') }, [message.id]) // eslint-disable-line react-hooks/exhaustive-deps

  const isDraft = message.status === 'draft'
  const canRegenerate = isDraft && (message.kind === 'cold' || message.kind === 'rfq_answer') // reply drafts are edit-only
  const toggle = (k: string) => setTones(tones.includes(k) ? tones.filter((x) => x !== k) : [...tones, k])

  async function save() {
    setBusy(true); setMsg(''); setErr('')
    try {
      onChange(await api<Message>(`/api/messages/${message.id}`, { method: 'PUT', json: { subject, body } }))
      setMsg(t('leads.draft.saved'))
    } catch (x) { setErr(x instanceof ApiError ? t(x.messageKey) : t('errors.network')) }
    setBusy(false)
  }

  async function regenerate() {
    setBusy(true); setMsg(''); setErr('')
    let rejected = false
    try {
      // Reject the superseded draft first: if that fails, no second draft is created.
      await api(`/api/messages/${message.id}/reject`, { method: 'POST', json: { reason: 'regenerated' } })
      rejected = true
      onReplace(await api<Message>(`/api/leads/${lead}/draft`, { method: 'POST', json: { tone: tones } }))
    } catch (x) {
      const m = x instanceof ApiError ? t(x.messageKey) : t('errors.network')
      setErr(m)
      if (rejected) onClose(m) // old draft is gone; parent closes it, reloads the lead and shows the error
    }
    setBusy(false)
  }

  return (
    <Card className="space-y-4">
      <div className="flex items-start justify-between gap-2">
        <h2 className="text-lg font-semibold">{t('leads.draft.title')}</h2>
        <Button variant="ghost" onClick={() => onClose()}>{t('leads.draft.close')}</Button>
      </div>
      <p role="note" className="bg-amber-50 border border-amber-300 rounded-md p-3 font-semibold">{t('leads.draft.notSent')}</p>
      {message.fallback && <p role="status" className="text-sm text-slate-700">{t('leads.draft.fallback')}</p>}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="space-y-3">
          <h3 className="font-semibold">{t('leads.draft.buyerLang', { lang: message.language.toUpperCase() })}</h3>
          <Field label={t('leads.draft.subject')}><Input value={subject} maxLength={200} disabled={!isDraft} onChange={(e) => setSubject(e.target.value)} /></Field>
          <Field label={t('leads.draft.body')}><Textarea rows={12} value={body} maxLength={5000} disabled={!isDraft} onChange={(e) => setBody(e.target.value)} /></Field>
        </div>
        <div className="space-y-3">
          <h3 className="font-semibold">{t('leads.draft.translation', { lang: (message.translation_language ?? i18n.language).toUpperCase() })}</h3>
          {message.translation_fallback || !message.body_tr
            ? <p role="status" className="text-slate-700 bg-slate-50 rounded-md p-3">{t('leads.draft.translationUnavailable')}</p>
            : <p className="whitespace-pre-wrap bg-slate-50 rounded-md p-3 min-h-11" data-testid="translation">{message.body_tr}</p>}
        </div>
      </div>
      {isDraft && (
        <>
          <Button onClick={save} disabled={busy || !subject.trim() || !body.trim()}>{t('leads.draft.save')}</Button>
          {canRegenerate && <fieldset className="space-y-2">
            <legend className="font-semibold">{t('leads.draft.tones')}</legend>
            <div className="flex flex-wrap gap-2">
              {TONES.map((k) => (
                <Button key={k} type="button" variant={tones.includes(k) ? 'primary' : 'secondary'} aria-pressed={tones.includes(k)} onClick={() => toggle(k)}>{t(`leads.draft.${k}`)}</Button>
              ))}
              <Button type="button" variant="secondary" onClick={regenerate} disabled={busy}>{t('leads.draft.regenerate')}</Button>
            </div>
          </fieldset>}
        </>
      )}
      {msg && <p role="status" className="font-semibold">{msg}</p>}
      {err && <p role="alert" className="text-brand font-semibold">{err}</p>}
      <Link to="/approvals" className="min-h-11 inline-flex items-center px-4 rounded-md font-semibold bg-navy text-white">{t('leads.draft.toApprovals')}</Link>
    </Card>
  )
}
