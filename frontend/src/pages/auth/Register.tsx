import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../../auth/AuthContext'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import Field from '../../components/ui/Field'
import Input from '../../components/ui/Input'
import Modal from '../../components/ui/Modal'
import { PrivacyText } from '../privacy/PrivacyNotice'

export default function Register() {
  const { t } = useTranslation()
  const { user, register } = useAuth()
  const nav = useNavigate()
  const [f, setF] = useState({ name: '', email: '', pw: '' })
  const [kvkk, setKvkk] = useState(false)
  const [modal, setModal] = useState(false)
  const [errs, setErrs] = useState<Record<string, string>>({})
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  if (user) return <Navigate to="/" replace />

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const v: Record<string, string> = {}
    if (!f.name.trim()) v.name = t('auth.nameRequired')
    if (f.pw.length < 8) v.pw = t('auth.passwordTooShort')
    if (!kvkk) v.kvkk = t('auth.kvkkRequired')
    setErrs(v)
    setErr('')
    if (Object.keys(v).length) return
    setBusy(true)
    try {
      await register(f.name.trim(), f.email, f.pw)
      nav('/onboarding')
    } catch (x) {
      setErr(t(x instanceof ApiError ? x.messageKey : 'errors.network'))
    } finally {
      setBusy(false)
    }
  }
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value })

  return (
    <Card className="max-w-md mx-auto">
      <h1 className="text-2xl font-semibold">{t('auth.registerTitle')}</h1>
      <p className="mb-4 text-slate-600">{t('auth.registerIntro')}</p>
      <form onSubmit={submit} className="space-y-4">
        <Field label={t('auth.name')} error={errs.name}><Input required autoComplete="name" value={f.name} onChange={set('name')} /></Field>
        <Field label={t('auth.email')}><Input type="email" required autoComplete="email" value={f.email} onChange={set('email')} /></Field>
        <Field label={t('auth.password')} hint={t('auth.passwordHint')} error={errs.pw}>
          <Input type="password" required autoComplete="new-password" value={f.pw} onChange={set('pw')} />
        </Field>
        <div>
          <label className="flex items-start gap-3 min-h-11 text-sm">
            <input type="checkbox" checked={kvkk} onChange={(e) => setKvkk(e.target.checked)} className="mt-1 size-5 accent-brand" />
            <span>
              {t('auth.kvkkLabel')}{' '}
              <button type="button" onClick={() => setModal(true)} className="underline font-semibold">{t('auth.kvkkLink')}</button>{' '}
              {t('auth.kvkkSuffix')}
            </span>
          </label>
          <p className="text-xs text-slate-600 mt-1">{t('auth.kvkkExplain')}</p>
          {errs.kvkk && <p role="alert" className="text-sm text-brand">{errs.kvkk}</p>}
        </div>
        {err && <p role="alert" className="text-brand font-semibold">{err}</p>}
        <Button type="submit" disabled={busy} className="w-full">{busy ? t('auth.submitting') : t('auth.submitRegister')}</Button>
      </form>
      <p className="mt-4 text-sm">{t('auth.haveAccount')} <Link to="/login" className="underline font-semibold">{t('auth.loginTitle')}</Link></p>
      {modal && <Modal title={t('privacy.title')} onClose={() => setModal(false)}><PrivacyText /></Modal>}
    </Card>
  )
}
