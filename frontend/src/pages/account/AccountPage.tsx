import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import Field from '../../components/ui/Field'
import Input from '../../components/ui/Input'

export default function AccountPage() {
  const { t } = useTranslation()
  const { logout } = useAuth()
  const nav = useNavigate()
  const [confirm, setConfirm] = useState('')
  const [pw, setPw] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  const download = async () => {
    setErr('')
    try {
      const res = await fetch('/api/account/export', { credentials: 'include' })
      if (!res.ok) throw new Error()
      const url = URL.createObjectURL(await res.blob())
      const a = document.createElement('a')
      a.href = url
      a.download = 'kobi-gpt-export.json'
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      setErr(t('errors.network'))
    }
  }

  const remove = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setErr('')
    try {
      await api('/api/account', { method: 'DELETE', json: { confirm, password: pw } })
      await logout().catch(() => undefined) // cookie is already cleared server-side; this resets client state
      nav('/login?deleted=1')
    } catch (x) {
      setErr(t(x instanceof ApiError ? x.messageKey : 'errors.network'))
      setBusy(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-semibold">{t('account.title')}</h1>
      <Card>
        <h2 className="text-lg font-semibold">{t('account.exportTitle')}</h2>
        <p className="text-slate-700 mb-3">{t('account.exportBody')}</p>
        <Button onClick={download}>{t('account.exportButton')}</Button>
        <p className="mt-3"><Link to="/privacy" className="underline inline-flex min-h-11 items-center">{t('nav.privacy')}</Link></p>
      </Card>
      <Card>
        <h2 className="text-lg font-semibold text-brand">{t('account.deleteTitle')}</h2>
        <p className="text-slate-700">{t('account.deleteWarning')}</p>
        <ul className="list-disc ml-6 my-3 text-slate-700">
          {Object.values(t('account.deleteList', { returnObjects: true }) as Record<string, string>).map((x) => <li key={x}>{x}</li>)}
        </ul>
        <form onSubmit={remove} className="space-y-4">
          <Field label={t('account.confirmLabel')} hint={t('account.confirmHint')}>
            <Input value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="off" required />
          </Field>
          <Field label={t('auth.password')}>
            <Input type="password" value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="current-password" required />
          </Field>
          {err && <p role="alert" className="text-brand font-semibold">{err}</p>}
          <Button type="submit" disabled={busy || !confirm || !pw}>{busy ? t('auth.submitting') : t('account.deleteButton')}</Button>
        </form>
      </Card>
    </div>
  )
}
