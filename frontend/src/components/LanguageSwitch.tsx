import { useTranslation } from 'react-i18next'
import { useAuth, type Lang } from '../auth/AuthContext'

export default function LanguageSwitch() {
  const { i18n, t } = useTranslation()
  const { setLanguage } = useAuth()
  return (
    <div role="group" aria-label={t('common.language')} className="flex items-center">
      {(['tr', 'en'] as Lang[]).map((l, i) => (
        <span key={l} className="flex items-center">
          {i > 0 && <span aria-hidden className="text-slate-400">|</span>}
          <button type="button" onClick={() => void setLanguage(l)} aria-pressed={i18n.language === l}
            className={`min-h-11 min-w-11 px-2 text-sm ${i18n.language === l ? 'font-bold underline underline-offset-4' : 'text-slate-600'}`}>
            {l.toUpperCase()}
          </button>
        </span>
      ))}
    </div>
  )
}
