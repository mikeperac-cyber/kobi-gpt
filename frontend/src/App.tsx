import { Route, Routes } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from './auth/AuthContext'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/auth/Login'
import Register from './pages/auth/Register'
import PrivacyNotice from './pages/privacy/PrivacyNotice'

// Placeholders: Task 8 builds onboarding, Task 9 the dashboard.
function Placeholder({ ns }: { ns: 'onboarding' | 'dashboard' }) {
  const { t } = useTranslation()
  const { user } = useAuth()
  return (
    <section>
      <h1 className="text-2xl font-semibold">{ns === 'dashboard' ? t('dashboard.welcome', { name: user?.name }) : t('onboarding.title')}</h1>
      <p className="text-slate-600">{t(`${ns}.soon`)}</p>
    </section>
  )
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/privacy" element={<PrivacyNotice />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<Placeholder ns="dashboard" />} />
          <Route path="/onboarding" element={<Placeholder ns="onboarding" />} />
        </Route>
      </Route>
    </Routes>
  )
}
