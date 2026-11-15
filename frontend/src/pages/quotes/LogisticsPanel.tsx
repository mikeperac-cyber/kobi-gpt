import { useTranslation } from 'react-i18next'
import Badge from '../../components/ui/Badge'
import { formatMoney, formatNumber } from '../../i18n/format'
import type { Estimate } from './types'

export default function LogisticsPanel({ est, included, total, currency }: { est: Estimate; included?: boolean; total?: number; currency?: string }) {
  const { t } = useTranslation()
  return (
    <section aria-label={t('logistics.panel')} className="space-y-2 border border-amber-300 bg-amber-50 rounded-md p-3">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-semibold">{t('logistics.panel')}</h3>
        <Badge className="bg-white! border border-amber-400">{t('logistics.estimatedTag')}</Badge>
        <Badge>{t(`logistics.mode.${est.mode}`, { defaultValue: est.mode })}</Badge>
      </div>
      <p className="text-sm font-semibold">{t('logistics.sampleNote')}</p>
      <ul className="space-y-1 text-sm">
        {est.lines.map((l) => (
          <li key={l.label_key} className="flex flex-wrap justify-between gap-x-3">
            <span><span className="font-semibold">{t(l.label_key)}</span> <span className="text-slate-700">— {l.formula}</span></span>
            <span className="font-semibold">{l.label_key.endsWith('.gross') ? t('logistics.kg', { n: formatNumber(l.value) }) : formatMoney(l.value, 'EUR')}</span>
          </li>
        ))}
      </ul>
      {included !== undefined && <p className="text-sm">{included ? t('quotes.freightIncluded') : t('quotes.freightExcluded')}</p>}
      {total !== undefined && currency && <p className="font-semibold">{t('quotes.total')}: {formatMoney(total, currency)}</p>}
    </section>
  )
}
