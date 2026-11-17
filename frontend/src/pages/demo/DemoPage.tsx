import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'

type DemoCo = { key: string; name: string; email: string }

export default function DemoPage() {
  const { t } = useTranslation()
  const { logout } = useAuth()
  const [cos, setCos] = useState<DemoCo[]>([])
  const [res, setRes] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState('')
  useEffect(() => {
    api<DemoCo[]>('/api/demo/companies').then(setCos).catch((x) => setErr(t(x instanceof ApiError ? x.messageKey : 'errors.network')))
  }, [t])

  const reset = async (key: string) => {
    setBusy(key); setErr('')
    try {
      const r = await api<{ elapsed_ms: number }>(`/api/demo/reset/${key}`, { method: 'POST' })
      setRes((p) => ({ ...p, [key]: t('demo.page.done', { ms: Math.round(r.elapsed_ms) }) }))
    } catch (x) { setErr(t(x instanceof ApiError ? x.messageKey : 'errors.network')) }
    finally { setBusy('') }
  }
  const loginAs = async (email: string) => {
    try { await logout() } catch { /* still leave */ }
    window.location.assign(`/login?email=${encodeURIComponent(email)}`) // full load: ProtectedRoute's own redirect would otherwise drop the query
  }
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{t('demo.page.title')}</h1>
      <p className="text-slate-600">{t('demo.page.intro')}</p>
      {err && <p role="alert" className="text-brand font-semibold">{err}</p>}
      <div className="grid gap-4 md:grid-cols-3">
        {cos.map((c) => (
          <Card key={c.key}>
            <h2 className="font-semibold">{c.name}</h2>
            <p className="text-sm text-slate-600 break-all">{c.email}</p>
            <div className="mt-3 flex flex-col gap-2">
              <Button disabled={!!busy} onClick={() => reset(c.key)}>{busy === c.key ? t('demo.page.resetting') : t('demo.page.reset')}</Button>
              <Button variant="secondary" onClick={() => loginAs(c.email)}>{t('demo.page.loginAs')}</Button>
            </div>
            <p role="status" className="mt-2 text-sm text-green-700 font-semibold">{res[c.key]}</p>
          </Card>
        ))}
      </div>
    </div>
  )
}
