import { useTranslation } from 'react-i18next'
import Badge from '../../components/ui/Badge'

const MARKETS = ['DE', 'NL', 'FR', 'US', 'AE', 'IQ']

export default function StepMarket() {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="step-h">
      <h2 id="step-h" className="text-xl font-semibold">{t('onboarding.marketTitle')}</h2>
      <p className="text-slate-600 mb-4">{t('onboarding.marketIntro')}</p>
      <ul className="space-y-2">
        {MARKETS.map((c) => {
          const on = c === 'DE'
          return (
            <li key={c}>
              <label className={`flex items-center gap-3 min-h-11 px-3 rounded-md border ${on ? 'border-navy bg-white' : 'border-slate-200 bg-slate-100 text-slate-500'}`}>
                <input type="radio" name="market" checked={on} disabled={!on} readOnly className="size-5 accent-brand" />
                <span className="flex-1">{t(`onboarding.markets.${c}`)}</span>
                {!on && <Badge>{t('onboarding.comingSoon')}</Badge>}
              </label>
            </li>
          )
        })}
      </ul>
      <p className="text-sm text-slate-600 mt-3">{t('onboarding.marketNote')}</p>
    </section>
  )
}
