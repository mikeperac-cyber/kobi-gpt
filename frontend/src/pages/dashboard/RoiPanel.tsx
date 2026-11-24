import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../../api/client'
import Card from '../../components/ui/Card'
import { formatMoney } from '../../i18n/format'

type Roi = { won_deals: number; valued_deals: number; totals: { currency: string; amount: number }[] }

/** Export deals won through the app, as the producer reported them. Shown only once there is one. */
export default function RoiPanel() {
  const { t } = useTranslation()
  const [data, setData] = useState<Roi | null>(null)
  useEffect(() => { api<Roi>('/api/dashboard/roi').then(setData).catch(() => setData(null)) }, [])
  if (!data || data.won_deals === 0) return null
  return (
    <Card className="space-y-2">
      <h2 className="text-lg font-semibold">{t('dashboard.roi.title')}</h2>
      <p>{t('dashboard.roi.count', { count: data.won_deals })}</p>
      <ul className="text-2xl font-bold">
        {data.totals.map((x) => <li key={x.currency}>{formatMoney(x.amount, x.currency)}</li>)}
      </ul>
      {data.valued_deals < data.won_deals && (
        <p className="text-sm text-slate-600">{t('dashboard.roi.missing', { count: data.won_deals - data.valued_deals })}</p>
      )}
      <p className="text-sm text-slate-600">{t('dashboard.roi.selfReported')}</p>
    </Card>
  )
}
