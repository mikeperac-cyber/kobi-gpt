import { Suspense, lazy } from 'react'
import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import AdminRoute from './components/AdminRoute'

const Login = lazy(() => import('./pages/auth/Login'))
const Register = lazy(() => import('./pages/auth/Register'))
const Wizard = lazy(() => import('./pages/onboarding/Wizard'))
const CompanyPage = lazy(() => import('./pages/company/CompanyPage'))
const ProductsPage = lazy(() => import('./pages/products/ProductsPage'))
const Dashboard = lazy(() => import('./pages/dashboard/Dashboard'))
const StorefrontPage = lazy(() => import('./pages/storefront/Index'))
const CompliancePage = lazy(() => import('./pages/compliance/Index'))
const LeadsPage = lazy(() => import('./pages/leads/LeadsTable'))
const LeadDetail = lazy(() => import('./pages/leads/LeadDetail'))
const ApprovalQueue = lazy(() => import('./pages/approvals/ApprovalQueue'))
const QuoteBuilder = lazy(() => import('./pages/quotes/QuoteBuilder'))
const Pipeline = lazy(() => import('./pages/pipeline/Pipeline'))
const LogisticsRates = lazy(() => import('./pages/admin/LogisticsRates'))
const AdminStats = lazy(() => import('./pages/admin/AdminStats'))
const KbList = lazy(() => import('./pages/admin/KbList'))
const DemoPage = lazy(() => import('./pages/demo/DemoPage'))
const AccountPage = lazy(() => import('./pages/account/AccountPage'))
const PrivacyNotice = lazy(() => import('./pages/privacy/PrivacyNotice'))

export default function App() {
  return (
    <Suspense fallback={null}>
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
          <Route path="/leads/:id" element={<LeadDetail />} />
          <Route path="/leads/:id/quote" element={<QuoteBuilder />} />
          <Route path="/approvals" element={<ApprovalQueue />} />
          <Route path="/account" element={<AccountPage />} />
          <Route path="/pipeline" element={<Pipeline />} />
          <Route element={<AdminRoute />}>
            <Route path="/demo" element={<DemoPage />} />
            <Route path="/admin/kb" element={<KbList />} />
            <Route path="/admin/stats" element={<AdminStats />} />
            <Route path="/admin/logistics-rates" element={<LogisticsRates />} />
          </Route>
        </Route>
      </Route>
    </Routes>
    </Suspense>
  )
}
