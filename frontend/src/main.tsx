import { StrictMode, Suspense, lazy } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource/noto-sans/latin-400.css'
import '@fontsource/noto-sans/latin-ext-400.css'
import '@fontsource/noto-sans/latin-600.css'
import '@fontsource/noto-sans/latin-ext-600.css'
import './index.css'
import PublicBoundary from './storefront/PublicBoundary'

// Buyer-facing routes load a separate chunk with no producer i18n/auth.
const isPublic = location.pathname.startsWith('/s/')
const PublicApp = lazy(() => import('./PublicApp'))
const ProducerRoot = lazy(() => import('./ProducerRoot'))

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {isPublic ? (
      <PublicBoundary>
        <Suspense fallback={null}>
          <PublicApp />
        </Suspense>
      </PublicBoundary>
    ) : (
      <Suspense fallback={null}>
        <ProducerRoot />
      </Suspense>
    )}
  </StrictMode>,
)
