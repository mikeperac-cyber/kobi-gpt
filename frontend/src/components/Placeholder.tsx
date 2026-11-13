import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

export default function Placeholder({ titleKey }: { titleKey: string }) {
  const { t } = useTranslation()
  return (
    <section className="space-y-3">
      <h1 className="text-2xl font-semibold">{t(titleKey)}</h1>
      <p className="text-slate-600">{t('dashboard.placeholder.empty')}</p>
      <Link to="/" className="underline min-h-11 inline-flex items-center">{t('dashboard.placeholder.back')}</Link>
    </section>
  )
}
