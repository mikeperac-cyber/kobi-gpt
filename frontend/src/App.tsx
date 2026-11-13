import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/auth/Login'
import Register from './pages/auth/Register'
import Wizard from './pages/onboarding/Wizard'
import CompanyPage from './pages/company/CompanyPage'
import ProductsPage from './pages/products/ProductsPage'
import Dashboard from './pages/dashboard/Dashboard'
import StorefrontPage from './pages/storefront/Index'
import CompliancePage from './pages/compliance/Index'
import LeadsPage from './pages/leads/Index'
import PrivacyNotice from './pages/privacy/PrivacyNotice'

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
          <Route path="/storefront" element={<StorefrontPage />} />
          <Route path="/compliance" element={<CompliancePage />} />
          <Route path="/leads" element={<LeadsPage />} />
        </Route>
      </Route>
    </Routes>
  )
}
