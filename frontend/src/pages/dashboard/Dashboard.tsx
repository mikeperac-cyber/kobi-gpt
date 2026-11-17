import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../../api/client'
import Button from '../../components/ui/Button'
import Flag from '../../components/Flag'
import Card from '../../components/ui/Card'
import Skeleton from '../../components/ui/Skeleton'
import ModuleCard from './ModuleCard'
import ImpactPanel from './ImpactPanel'
import Notifications, { type Notif } from './Notifications'
import Roadmap, { type RoadmapState } from './Roadmap'

type Data = {
  company: { name: string; country_code: string }
  storefront: { status: 'none' | 'draft' | 'published'; slug: string | null }
  compliance: { score: number | null }
  leads: { count: number; pending_approvals: number }
  roadmap: RoadmapState
  notifications: Notif[]
}

export default function Dashboard() {
  const { t } = useTranslation()
  const [data, setData] = useState<Data | null>(null)
  const [failed, setFailed] = useState(false)
  const load = useCallback(() => {
    setFailed(false)
    api<Data>('/api/dashboard').then(setData).catch(() => setFailed(true))
  }, [])
  useEffect(() => { load() }, [load])

  const markRead = (id: string) => {
    setData((d) => d && { ...d, notifications: d.notifications.map((n) => (n.id === id ? { ...n, read: true } : n)) })
    api(`/api/notifications/${id}/read`, { method: 'POST' }).catch(load)
  }

  if (failed) return (
    <Card role="alert" className="text-center space-y-3">
      <p>{t('dashboard.loadError')}</p>
      <Button onClick={load}>{t('dashboard.retry')}</Button>
    </Card>
  )
  if (!data) return (
    <div aria-busy="true" className="space-y-4">
      <Skeleton className="h-8 w-64" /><Skeleton className="h-24 w-full" />
      <div className="grid gap-4 sm:grid-cols-3"><Skeleton className="h-40" /><Skeleton className="h-40" /><Skeleton className="h-40" /></div>
    </div>
  )
  const { storefront: sf, compliance: c, leads: l } = data
  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">{t('dashboard.title')}</h1>
        <p className="text-slate-700">
          {data.company.name} <Flag country={data.company.country_code} />
        </p>
      </header>
      <Roadmap roadmap={data.roadmap} />
      <div className="grid gap-4 sm:grid-cols-3">
        <ModuleCard title={t('dashboard.storefront.title')} badge={t(`dashboard.storefront.${sf.status}`)} tone={sf.status === 'published' ? 'good' : 'neutral'}
          to="/storefront" cta={t(sf.status === 'none' ? 'dashboard.storefront.create' : 'dashboard.storefront.view')} />
        <ModuleCard title={t('dashboard.compliance.title')} badge={c.score == null ? t('dashboard.compliance.none') : t('dashboard.compliance.score', { score: c.score })}
          tone={c.score == null ? 'neutral' : 'good'} to="/compliance" cta={t('dashboard.compliance.run')} />
        <ModuleCard title={t('dashboard.leads.title')} badge={t('dashboard.leads.summary', { count: l.count, pending: l.pending_approvals })}
          to="/leads" cta={t('dashboard.leads.find')} />
      </div>
      <ImpactPanel />
      <Notifications items={data.notifications} onRead={markRead} />
    </section>
  )
}
