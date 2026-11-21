import { useEffect, useState } from 'react'
import { PageSkeleton } from '../../components/ui/Skeleton'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../../api/client'
import DemoBadge from '../../components/DemoBadge'
import Card from '../../components/ui/Card'
import type { Lead } from '../leads/types'

type Stats = { leads: number; messages_sent: number; replies: number; quotes_sent: number; won: number }
const COLS = ['new', 'draft_ready', 'sent', 'replied', 'quoted', 'won', 'lost', 'do_not_contact'] as const
const COUNTERS = ['leads', 'messages_sent', 'replies', 'quotes_sent', 'won'] as const

export default function Pipeline() {
  const { t } = useTranslation()
  const [leads, setLeads] = useState<Lead[] | null>(null)
  const [stats, setStats] = useState<Stats | null>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    Promise.all([api<Lead[]>('/api/leads?sort=score&limit=500'), api<Stats>('/api/pipeline/stats')])
      .then(([l, s]) => { setLeads(l); setStats(s) }).catch(() => setFailed(true))
  }, [])

  if (failed) return <p role="alert" className="text-brand font-semibold">{t('pipeline.loadError')}</p>
  if (!leads || !stats) return <PageSkeleton />
  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">{t('pipeline.title')}</h1>
      <dl className="grid grid-cols-2 sm:grid-cols-5 gap-2">
        {COUNTERS.map((k) => (
          <Card key={k} className="p-3!">
            <dt className="text-sm text-slate-700">{t(`pipeline.stats.${k}`)}</dt>
            <dd className="text-2xl font-bold" data-testid={`stat-${k}`}>{stats[k]}</dd>
          </Card>
        ))}
      </dl>
      <p className="text-sm text-slate-600">{t('pipeline.statsNote')}</p>
      {leads.length === 0 && <Link to="/leads" className="min-h-11 inline-flex items-center px-4 rounded-md font-semibold bg-brand text-white">{t('dashboard.leads.find')}</Link>}
      <div className="overflow-x-auto pb-2">
        <div className="flex gap-3 min-w-max">
          {COLS.map((c) => {
            const col = leads.filter((l) => l.status === c)
            return (
              <section key={c} aria-label={t(`pipeline.col.${c}`)} className="w-60 shrink-0 bg-slate-100 rounded-lg p-2 space-y-2">
                <h2 className="font-semibold text-sm px-1">{t(`pipeline.col.${c}`)} <span className="text-slate-600">({col.length})</span></h2>
                {col.length === 0 && <p className="text-sm text-slate-600 px-1">{t('pipeline.empty')}</p>}
                {col.map((l) => (
                  <Link key={l.id} to={`/leads/${l.id}`} className="block bg-white rounded-md border border-slate-200 p-3 min-h-11 space-y-1">
                    <span className="font-semibold block">{l.company_name}</span>
                    <span className="text-sm text-slate-700 block">{l.country} · {t('leads.colScore')}: {l.score}</span>
                    {l.is_demo && <DemoBadge />}
                  </Link>
                ))}
              </section>
            )
          })}
        </div>
      </div>
    </section>
  )
}
