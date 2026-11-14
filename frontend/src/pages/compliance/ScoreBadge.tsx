import { useId, useState } from 'react'
import { useTranslation } from 'react-i18next'
import Card from '../../components/ui/Card'

export default function ScoreBadge({ score }: { score: number }) {
  const { t } = useTranslation()
  const id = useId()
  const [open, setOpen] = useState(false)
  return (
    <Card className="flex flex-wrap items-center gap-3">
      <p className="text-2xl font-bold" aria-live="polite">{t('compliance.score', { score })}</p>
      <span className="text-sm rounded-full bg-slate-100 px-2.5 py-1 font-semibold">{t('compliance.estimated')}</span>
      <button type="button" aria-label={t('compliance.formulaButton')} aria-expanded={open} aria-describedby={id}
        onClick={() => setOpen((o) => !o)}
        className="min-h-11 min-w-11 rounded-full border border-slate-300 font-bold focus-visible:outline-2 focus-visible:outline-navy">i</button>
      <p id={id} hidden={!open} className="basis-full text-sm text-slate-700">{t('compliance.formula')}</p>
    </Card>
  )
}
