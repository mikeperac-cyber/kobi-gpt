import { Route, Routes } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from './auth/AuthContext'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/auth/Login'
import Register from './pages/auth/Register'
import Wizard from './pages/onboarding/Wizard'
import CompanyPage from './pages/company/CompanyPage'
import ProductsPage from './pages/products/ProductsPage'
import PrivacyNotice from './pages/privacy/PrivacyNotice'

// Placeholder: Task 9 builds the dashboard.
function Dashboard() {
  const { t } = useTranslation()
  const { user } = useAuth()
  return (
    <section>
      <h1 className="text-2xl font-semibold">{t('dashboard.welcome', { name: user?.name })}</h1>
      <p className="text-slate-600">{t('dashboard.soon')}</p>
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
          <Route path="/" element={<Dashboard />} />
          <Route path="/onboarding" element={<Wizard />} />
          <Route path="/company" element={<CompanyPage />} />
          <Route path="/products" element={<ProductsPage />} />
        </Route>
      </Route>
    </Routes>
  )
}
