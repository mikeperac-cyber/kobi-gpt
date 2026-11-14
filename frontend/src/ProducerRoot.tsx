import { Suspense, lazy } from 'react'
import ErrorBoundary from './components/ErrorBoundary'
import './i18n'

const ProducerApp = lazy(() => import('./ProducerApp'))

// Boundary above the lazy chunk so a failed ProducerApp load shows the tr/en copy; no AuthProvider needed.
export default function ProducerRoot() {
  return (
    <ErrorBoundary>
      <Suspense fallback={null}>
        <ProducerApp />
      </Suspense>
    </ErrorBoundary>
  )
}
