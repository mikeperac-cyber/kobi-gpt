import { useEffect, useRef } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/AuthContext'
import LanguageSwitch from './LanguageSwitch'
import Button from './ui/Button'
import RfqToast from './RfqToast'
import { useRfqAlerts } from '../hooks/useRfqAlerts'

export default function Layout() {
  const { t } = useTranslation()
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const { pathname } = useLocation()
  const main = useRef<HTMLElement>(null)
  const first = useRef(true)
  const { alerts, dismiss } = useRfqAlerts(!!user?.has_company)
  // keyboard users: a route change must not leave focus on a removed element
  useEffect(() => { if (first.current) { first.current = false; return } main.current?.focus() }, [pathname])
  return (
    <div className="min-h-screen flex flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:p-2">{t('nav.skip')}</a>
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-4 py-1 flex flex-wrap items-center justify-between gap-x-2">
          <Link to="/" className="font-bold text-lg min-h-11 inline-flex items-center">
            <span className="text-brand">KOBİ</span>-GPT
          </Link>
          <div className="flex flex-wrap items-center gap-x-1">
            <LanguageSwitch />
            {user?.is_admin && <NavLink to="/admin/kb" className="min-h-11 px-3 inline-flex items-center text-sm font-semibold">{t('nav.admin')}</NavLink>}
            {user?.is_admin && <NavLink to="/admin/stats" className="min-h-11 px-3 inline-flex items-center text-sm font-semibold">{t('nav.stats')}</NavLink>}
            {user?.is_admin && <NavLink to="/admin/logistics-rates" className="min-h-11 px-3 inline-flex items-center text-sm font-semibold">{t('nav.rates')}</NavLink>}
            {user && <NavLink to="/account" className="min-h-11 px-3 inline-flex items-center text-sm font-semibold">{t('nav.account')}</NavLink>}
            {user && (
              <Button variant="ghost" onClick={async () => { try { await logout() } catch { /* still leave */ } nav('/login') }}>{t('auth.logout')}</Button>
            )}
          </div>
        </div>
        {user?.has_company && (
          <nav aria-label={t('nav.main')} className="max-w-5xl mx-auto px-4 flex gap-1 overflow-x-auto border-t border-slate-100">
            {([['/', 'nav.dashboard'], ['/company', 'nav.company'], ['/products', 'nav.products'], ['/storefront', 'nav.storefront'], ['/compliance', 'nav.compliance'], ['/leads', 'nav.leads'], ['/approvals', 'nav.approvals'], ['/pipeline', 'nav.pipeline']] as const).map(([to, k]) => (
              <NavLink key={to} to={to} end className={({ isActive }) => `min-h-11 px-3 inline-flex items-center text-sm ${isActive ? 'font-bold underline underline-offset-4 decoration-brand' : 'text-slate-700'}`}>{t(k)}</NavLink>
            ))}
          </nav>
        )}
      </header>
      <main id="main" ref={main} tabIndex={-1} className="outline-none flex-1 w-full max-w-5xl mx-auto px-4 py-6"><Outlet /></main>
      <RfqToast alerts={alerts} onClose={dismiss} />
      <footer className="text-center text-sm text-slate-600 py-4">
        <Link to="/privacy" className="underline inline-flex min-h-11 items-center">{t('nav.privacy')}</Link>
      </footer>
    </div>
  )
}
