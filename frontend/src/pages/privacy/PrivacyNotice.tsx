import { useTranslation } from 'react-i18next'

const SECTIONS = ['controller', 'purpose', 'basis', 'rights', 'contact'] as const

export function PrivacyText() {
  const { t } = useTranslation()
  return (
    <div className="space-y-3 text-sm leading-relaxed">
      <p>{t('privacy.intro')}</p>
      {SECTIONS.map((s) => (
        <section key={s}>
          <h3 className="font-semibold">{t(`privacy.${s}Title`)}</h3>
          <p>{t(`privacy.${s}`)}</p>
        </section>
      ))}
      <p className="text-slate-600">{t('privacy.placeholderNote')}</p>
    </div>
  )
}

export default function PrivacyNotice() {
  const { t } = useTranslation()
  return (
    <article>
      <h1 className="text-2xl font-semibold mb-4">{t('privacy.title')}</h1>
      <PrivacyText />
    </article>
  )
}
