import { useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../../api/client'
import CompanyFields, { companyFromDoc, companyPayload, serverErrs, translateErrs, type CompanyDoc, type CompanyDraft } from '../../components/CompanyFields'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import Skeleton from '../../components/ui/Skeleton'

export default function CompanyPage() {
  const { t } = useTranslation()
  const [draft, setDraft] = useState<CompanyDraft | null>(null)
  const [errs, setErrs] = useState<Record<string, string>>({})
  const [top, setTop] = useState('')
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api<CompanyDoc>('/api/company').then((c) => setDraft(companyFromDoc(c))).catch((x) => setTop(serverErrs(x).top))
  }, [])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!draft) return
    setSaved(false)
    setTop('')
    const { payload, errs: ve } = companyPayload(draft)
    setErrs(ve)
    if (Object.keys(ve).length) return
    setBusy(true)
    try {
      setDraft(companyFromDoc(await api<CompanyDoc>('/api/company', { method: 'PUT', json: payload })))
      setSaved(true)
    } catch (x) {
      const s = serverErrs(x)
      setErrs(s.fields)
      setTop(s.top)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-semibold mb-4">{t('company.pageTitle')}</h1>
      {!draft && !top && <div role="status" aria-label={t('common.loading')} className="space-y-3"><Skeleton className="h-11" /><Skeleton className="h-11" /><Skeleton className="h-24" /></div>}
      {draft && (
        <form onSubmit={submit} noValidate>
          <CompanyFields value={draft} onChange={(d) => { setDraft(d); setSaved(false) }} errs={translateErrs(t, errs)} />
          {top && <p role="alert" className="text-brand font-semibold mt-4">{t(top)}</p>}
          {saved && <p role="status" className="text-green-800 font-semibold mt-4">{t('company.saved')}</p>}
          <Button type="submit" disabled={busy} className="w-full mt-6">{busy ? t('auth.submitting') : t('common.save')}</Button>
        </form>
      )}
      {!draft && top && <p role="alert" className="text-brand font-semibold">{t(top)}</p>}
    </Card>
  )
}
