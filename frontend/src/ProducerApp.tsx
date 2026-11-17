import { BrowserRouter } from 'react-router-dom'
import './i18n'
import App from './App'
import { AuthProvider } from './auth/AuthContext'
import { DemoGuideProvider } from './components/DemoGuide'
import ErrorBoundary from './components/ErrorBoundary'

export default function ProducerApp() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <DemoGuideProvider><App /></DemoGuideProvider>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
