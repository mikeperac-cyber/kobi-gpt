import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import { api } from '../../api/client'
import Card from '../../components/ui/Card'

type Impact = {
  measured_from: 'signup' | 'demo_reset'
  durations_s: { to_storefront: number | null; to_report: number | null; to_outreach: number | null }
}

/** Human duration from whole seconds, two largest units at most; localized via i18n. */
export function humanDuration(s: number, t: TFunction) {
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60
  if (d) return t('impact.d', { d })
  if (h) return t('impact.hm', { h, m })
  if (m) return t('impact.ms', { m, s: sec })
  return t('impact.s', { s: sec })
}

export default function ImpactPanel() {
  const { t } = useTranslation()
  const [data, setData] = useState<Impact | null>(null)
  useEffect(() => { api<Impact>('/api/dashboard/impact').then(setData).catch(() => setData(null)) }, [])
  if (!data) return null
  const rows: [string, number | null][] = [
    ['to_storefront', data.durations_s.to_storefront], ['to_report', data.durations_s.to_report],
    ['to_outreach', data.durations_s.to_outreach]]
  return (
    <Card className="space-y-2">
      <h2 className="text-lg font-semibold">{t('impact.title')}</h2>
      <p className="text-sm text-slate-700">{t(data.measured_from === 'demo_reset' ? 'impact.sinceReset' : 'impact.sinceSignup')}</p>
      <dl className="space-y-1">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-4">
            <dt>{t(`impact.${k}`)}</dt>
            <dd className="font-semibold">{v == null ? t('impact.notYet') : humanDuration(v, t)}</dd>
          </div>
        ))}
      </dl>
      <p className="text-xs text-slate-600">{t('impact.note')}</p>
    </Card>
  )
}
