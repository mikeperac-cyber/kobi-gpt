import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../../api/client'
import { useOnRfq } from '../../hooks/useRfqAlerts'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Select from '../../components/ui/Select'
import { PageSkeleton } from '../../components/ui/Skeleton'
import DemoBadge from '../../components/DemoBadge'
import { formatDate } from '../../i18n/format'
import CsvImport from './CsvImport'
import LeadForm from './LeadForm'
import ScoreBreakdown from './ScoreBreakdown'
import { STATUSES, type Lead } from './types'

const PAGE = 100

export default function LeadsTable() {
  const { t } = useTranslation()
  const [leads, setLeads] = useState<Lead[] | null>(null)
  const [sort, setSort] = useState('')
  const [status, setStatus] = useState('')
  const [panel, setPanel] = useState<'' | 'csv' | 'form'>('')
  const [failed, setFailed] = useState(false)
  const [total, setTotal] = useState(0)
  const [more, setMore] = useState(false)

  // offset 0 replaces the list (reload, filter, sort); a later offset appends the next page
  const fetchPage = useCallback(async (offset: number) => {
    const q = new URLSearchParams({ limit: String(PAGE), offset: String(offset) })
    if (sort) q.set('sort', sort)
    if (status) q.set('status', status)
    const page = await api<Lead[]>(`/api/leads?${q}`, { onHeaders: (h) => setTotal(Number(h.get('X-Total-Count') ?? 0)) })
    setLeads((prev) => (offset && prev ? [...prev, ...page] : page))
  }, [sort, status])
  const load = useCallback(async () => {
    try { await fetchPage(0); setFailed(false) } catch { setFailed(true) }
  }, [fetchPage])
  const loadMore = async () => {
    setMore(true)
    try { await fetchPage(leads?.length ?? 0); setFailed(false) } catch { setFailed(true) } finally { setMore(false) }
  }
  useEffect(() => { void load() }, [load])
  useOnRfq(load)

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">{t('leads.title')}</h1>
      <p className="text-slate-700">{t('leads.intro')}</p>
      <div className="flex flex-wrap items-end gap-2">
        <Button onClick={() => setPanel('csv')}>{t('leads.importCsv')}</Button>
        <Button variant="secondary" onClick={() => setPanel('form')}>{t('leads.addManual')}</Button>
        <label className="text-sm font-semibold sm:ml-auto">{t('leads.sortLabel')}
          <Select value={sort} onChange={(e) => setSort(e.target.value)} className="mt-1 font-normal">
            <option value="">{t('leads.sortDefault')}</option>
            <option value="score">{t('leads.sortScore')}</option>
            <option value="created_at">{t('leads.sortDate')}</option>
          </Select>
        </label>
        <label className="text-sm font-semibold">{t('leads.filterLabel')}
          <Select value={status} onChange={(e) => setStatus(e.target.value)} className="mt-1 font-normal">
            <option value="">{t('leads.filterAll')}</option>
            {STATUSES.map((s) => <option key={s} value={s}>{t(`leads.status.${s}`)}</option>)}
          </Select>
        </label>
      </div>
      {panel === 'csv' && <CsvImport onDone={load} onCancel={() => setPanel('')} />}
      {panel === 'form' && <LeadForm onDone={() => { setPanel(''); void load() }} onCancel={() => setPanel('')} />}
      {failed && <p role="alert" className="text-brand font-semibold">{t('errors.network')}</p>}
      {!leads && !failed && <PageSkeleton />}
      {leads && leads.length === 0 && <div className="py-6 space-y-3"><p className="text-slate-700">{status ? t('leads.emptyFiltered') : t('leads.empty')}</p>{status ? <Button variant="secondary" onClick={() => setStatus('')}>{t('leads.filterAll')}</Button> : <Button onClick={() => setPanel('csv')}>{t('leads.importCsv')}</Button>}</div>}
      {leads && leads.length > 0 && (
        <div className="overflow-x-auto bg-white border border-slate-200 rounded-lg">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left bg-slate-50">
                {(['colCompany', 'colCountry', 'colSource', 'colScore', 'colStatus', 'colCreated'] as const).map((k) => <th key={k} scope="col" className="px-3 py-2">{t(`leads.${k}`)}</th>)}
              </tr>
            </thead>
            <tbody>
              {leads.map((l) => (
                <tr key={l.id} className="border-t border-slate-100 align-middle">
                  <td className="px-3 py-1">
                    <Link to={`/leads/${l.id}`} className="font-semibold underline min-h-11 inline-flex items-center">{l.company_name}</Link>
                    {l.is_demo && <div><DemoBadge /></div>}
                  </td>
                  <td className="px-3 py-1 whitespace-nowrap">{l.country}</td>
                  <td className="px-3 py-1 whitespace-nowrap">{l.source === 'rfq' ? <Badge className="bg-brand! text-white!">{t('leads.hot')}</Badge> : t(`leads.src.${l.source}`)}</td>
                  <td className="px-3 py-1"><ScoreBreakdown score={l.score} breakdown={l.score_breakdown} /></td>
                  <td className="px-3 py-1 whitespace-nowrap">{t(`leads.status.${l.status}`)}</td>
                  <td className="px-3 py-1 whitespace-nowrap">{formatDate(l.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {leads && leads.length > 0 && total > leads.length && (
        <div className="flex items-center gap-3">
          <span className="text-sm text-slate-600">{t('leads.shown', { n: leads.length, total })}</span>
          <Button variant="secondary" disabled={more} onClick={() => void loadMore()}>{t('leads.loadMore')}</Button>
        </div>
      )}
    </section>
  )
}
