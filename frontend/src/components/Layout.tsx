import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/AuthContext'
import LanguageSwitch from './LanguageSwitch'
import Button from './ui/Button'

export default function Layout() {
  const { t } = useTranslation()
  const { user, logout } = useAuth()
  const nav = useNavigate()
  return (
    <div className="min-h-screen flex flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:p-2">{t('nav.skip')}</a>
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-4 py-1 flex items-center justify-between gap-2">
          <Link to="/" className="font-bold text-lg min-h-11 inline-flex items-center">
            <span className="text-brand">KOBİ</span>-GPT
          </Link>
          <div className="flex items-center gap-1">
            <LanguageSwitch />
            {user && (
              <Button variant="ghost" onClick={async () => { try { await logout() } catch { /* still leave */ } nav('/login') }}>{t('auth.logout')}</Button>
            )}
          </div>
        </div>
      </header>
      <main id="main" className="flex-1 w-full max-w-5xl mx-auto px-4 py-6"><Outlet /></main>
      <footer className="text-center text-sm text-slate-600 py-4">
        <Link to="/privacy" className="underline inline-flex min-h-11 items-center">{t('nav.privacy')}</Link>
      </footer>
    </div>
  )
}
