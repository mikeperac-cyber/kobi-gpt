import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import Field from '../../components/ui/Field'
import Input from '../../components/ui/Input'
import Textarea from '../../components/ui/Textarea'

export function SourceNoteField({ value, onChange }: { value: string; onChange(v: string): void }) {
  const { t } = useTranslation()
  return (
    <Field label={t('leads.sourceNoteLabel')} hint={t('leads.sourceNoteHint')}>
      <Input value={value} maxLength={200} required placeholder={t('leads.sourceNotePlaceholder')} onChange={(e) => onChange(e.target.value)} />
    </Field>
  )
}

const empty = { company_name: '', country: 'DE', contact_name: '', email: '', website: '', notes: '', source_note: '' }

export default function LeadForm({ onDone, onCancel }: { onDone(): void; onCancel(): void }) {
  const { t } = useTranslation()
  const [f, setF] = useState(empty)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k: keyof typeof empty) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value })

  async function submit(e: FormEvent) {
    e.preventDefault()
    setErr(''); setBusy(true)
    try {
      await api('/api/leads', { method: 'POST', json: { ...f, website: f.website.trim() || null } })
      onDone()
    } catch (x) {
      setErr(x instanceof ApiError ? t(x.messageKey) : t('errors.network'))
    }
    setBusy(false)
  }

  return (
    <Card>
      <form onSubmit={submit} className="space-y-3">
        <h2 className="text-lg font-semibold">{t('leads.form.title')}</h2>
        <Field label={t('leads.form.company_name')}><Input required maxLength={200} value={f.company_name} onChange={set('company_name')} /></Field>
        <div className="grid sm:grid-cols-2 gap-3">
          <Field label={t('leads.form.country')}><Input required maxLength={2} value={f.country} onChange={set('country')} /></Field>
          <Field label={t('leads.form.contact_name')}><Input value={f.contact_name} onChange={set('contact_name')} /></Field>
          <Field label={t('leads.form.email')}><Input type="email" value={f.email} onChange={set('email')} /></Field>
          <Field label={t('leads.form.website')}><Input value={f.website} onChange={set('website')} /></Field>
        </div>
        <Field label={t('leads.form.notes')}><Textarea value={f.notes} maxLength={2000} onChange={set('notes')} /></Field>
        <SourceNoteField value={f.source_note} onChange={(v) => setF({ ...f, source_note: v })} />
        {err && <p role="alert" className="text-brand font-semibold">{err}</p>}
        <div className="flex gap-2">
          <Button type="submit" disabled={busy}>{t('leads.form.submit')}</Button>
          <Button type="button" variant="secondary" onClick={onCancel}>{t('common.cancel')}</Button>
        </div>
      </form>
    </Card>
  )
}
