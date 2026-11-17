import { useEffect, useState } from 'react'
import { PageSkeleton } from '../../components/ui/Skeleton'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../../api/client'
import Card from '../../components/ui/Card'
import { formatNumber } from '../../i18n/format'

const KEYS = ['companies', 'storefronts_published', 'reports', 'approved_messages', 'rfqs'] as const
type Counts = Record<(typeof KEYS)[number], number>
type Stats = Counts & { excluding_demo: Counts }

export default function AdminStats() {
  const { t } = useTranslation()
  const [s, setS] = useState<Stats | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => { api<Stats>('/api/admin/stats').then(setS).catch((x) => setErr(x instanceof ApiError ? t(x.messageKey) : t('errors.network'))) }, [t])
  if (!s) return <PageSkeleton error={err} />
  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">{t('adminStats.title')}</h1>
      <Card>
        <table className="w-full text-left">
          <thead><tr><th scope="col" /><th scope="col">{t('adminStats.all')}</th><th scope="col">{t('adminStats.excludingDemo')}</th></tr></thead>
          <tbody>
            {KEYS.map((k) => (
              <tr key={k}><th scope="row" className="font-normal">{t(`adminStats.${k}`)}</th>
                <td>{formatNumber(s[k])}</td><td>{formatNumber(s.excluding_demo[k])}</td></tr>
            ))}
          </tbody>
        </table>
      </Card>
      <p className="text-xs text-slate-600">{t('adminStats.note')}</p>
    </section>
  )
}
