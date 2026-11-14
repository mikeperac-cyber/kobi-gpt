import { useTranslation } from 'react-i18next'
import Badge from '../../components/ui/Badge'
import Card from '../../components/ui/Card'
import VerifiedBadge from '../../components/VerifiedBadge'
import type { Item } from './types'

const LEVEL_CLS = { zorunlu: 'bg-red-100 text-red-900', koşullu: 'bg-amber-100 text-amber-900', önerilen: 'bg-slate-100 text-navy' }

export default function ChecklistItem({ item, onTick }: { item: Item; onTick?(done: boolean): void }) {
  const { t, i18n } = useTranslation()
  const title = i18n.language === 'en' ? item.title_en || item.title_tr : item.title_tr
  const ref = `${item.rule_id}-t`
  return (
    <Card className="space-y-2" data-rule={item.rule_id}>
      <div className="flex flex-wrap items-center gap-2">
        <h3 id={ref} className="font-semibold">{title}</h3>
        <Badge className={LEVEL_CLS[item.level]}>{t(`compliance.level.${item.level}`)}</Badge>
        <VerifiedBadge verified={!!item.verified} lastVerified={item.last_verified} />
      </div>
      {item.summary && (
        <p><span className="text-xs font-semibold text-slate-600 block">{t('compliance.officialText')}</span>{item.summary}</p>
      )}
      {item.reason && item.reason !== item.summary && (
        <p className="rounded-md bg-slate-50 border border-slate-200 p-2 text-sm">
          <span className="text-xs font-semibold text-slate-600 block">{t('compliance.aiExplanation')}</span>{item.reason}
        </p>
      )}
      {item.next_step && <p className="text-sm"><b>{t('compliance.nextStep')}: </b>{item.next_step}</p>}
      {item.source_url && (
        <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="text-sm underline text-navy break-all">
          {t('compliance.source')}: {item.source_url}
        </a>
      )}
      {onTick && (
        <label className="flex items-center gap-3 min-h-11 cursor-pointer">
          <input type="checkbox" className="w-5 h-5" checked={!!item.done} aria-labelledby={ref} onChange={(e) => onTick(e.target.checked)} />
          <span>{t('compliance.done')}</span>
        </label>
      )}
    </Card>
  )
}
