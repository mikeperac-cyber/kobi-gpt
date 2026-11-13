import { useTranslation } from 'react-i18next'
import { translateErrs } from '../../components/CompanyFields'
import ProductForm, { type ProductDraft } from '../../components/ProductForm'

export default function StepProduct({ value, onChange, errs }: { value: ProductDraft; onChange(v: ProductDraft): void; errs: Record<string, string> }) {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="step-h">
      <h2 id="step-h" className="text-xl font-semibold">{t('onboarding.productTitle')}</h2>
      <p className="text-slate-600 mb-4">{t('onboarding.productIntro')}</p>
      <ProductForm mode="onboarding" value={value} onChange={onChange} errs={translateErrs(t, errs)} />
    </section>
  )
}
