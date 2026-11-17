import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../../auth/AuthContext'
import { ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import Field from '../../components/ui/Field'
import Input from '../../components/ui/Input'

export default function Login() {
  const { t } = useTranslation()
  const { user, login } = useAuth()
  const nav = useNavigate()
  const [params] = useSearchParams()
  const [email, setEmail] = useState(() => params.get('email') ?? '')
  const [pw, setPw] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  if (user) return <Navigate to="/" replace />

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setErr('')
    try {
      await login(email, pw)
      nav('/')
    } catch (x) {
      setErr(t(x instanceof ApiError ? x.messageKey : 'errors.network'))
    } finally {
      setBusy(false)
    }
  }
  return (
    <Card className="max-w-md mx-auto">
      <h1 className="text-2xl font-semibold">{t('auth.loginTitle')}</h1>
      {params.get('deleted') && <p role="status" className="mb-3 text-green-800 font-semibold">{t('auth.deletedNotice')}</p>}
      <p className="mb-4 text-slate-600">{t('auth.loginIntro')}</p>
      <form onSubmit={submit} className="space-y-4">
        <Field label={t('auth.email')}><Input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
        <Field label={t('auth.password')}><Input type="password" required autoComplete="current-password" value={pw} onChange={(e) => setPw(e.target.value)} /></Field>
        {err && <p role="alert" className="text-brand font-semibold">{err}</p>}
        <Button type="submit" disabled={busy} className="w-full">{busy ? t('auth.submitting') : t('auth.submitLogin')}</Button>
      </form>
      <p className="mt-4 text-sm">{t('auth.noAccount')} <Link to="/register" className="underline font-semibold">{t('auth.registerTitle')}</Link></p>
    </Card>
  )
}
