import { useTranslation } from 'react-i18next'
import Card from '../../components/ui/Card'

export type RoadmapState = { profile: boolean; storefront: boolean; compliance: boolean; first_quote: boolean }
const STEPS = ['profile', 'storefront', 'compliance', 'first_quote'] as const

export default function Roadmap({ roadmap }: { roadmap: RoadmapState }) {
  const { t } = useTranslation()
  const done = STEPS.filter((s) => roadmap[s]).length
  return (
    <Card>
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="font-semibold">{t('dashboard.roadmap.title')}</h2>
        <span className="text-sm text-slate-600">{t('dashboard.roadmap.progress', { done })}</span>
      </div>
      <ol className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {STEPS.map((s, i) => (
          <li key={s} className={`rounded-md border px-3 py-2 text-sm ${roadmap[s] ? 'bg-green-50 border-green-600 text-green-900' : 'bg-white border-slate-300 text-slate-700'}`}>
            <span className="font-semibold">{i + 1}. {t(`dashboard.roadmap.${s}`)}</span>
            <span className="block text-xs">{roadmap[s] ? `✓ ${t('dashboard.roadmap.done')}` : t('dashboard.roadmap.todo')}</span>
          </li>
        ))}
      </ol>
    </Card>
  )
}
