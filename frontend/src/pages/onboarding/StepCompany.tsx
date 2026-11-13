import { useTranslation } from 'react-i18next'
import CompanyFields, { translateErrs, type CompanyDraft } from '../../components/CompanyFields'

export default function StepCompany({ value, onChange, errs }: { value: CompanyDraft; onChange(v: CompanyDraft): void; errs: Record<string, string> }) {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="step-h">
      <h2 id="step-h" className="text-xl font-semibold">{t('onboarding.companyTitle')}</h2>
      <p className="text-slate-600 mb-4">{t('onboarding.companyIntro')}</p>
      <CompanyFields value={value} onChange={onChange} errs={translateErrs(t, errs)} />
    </section>
  )
}
