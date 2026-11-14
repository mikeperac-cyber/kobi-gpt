import { lazy } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import PublicStorefront from './storefront/PublicStorefront'

const Legal = lazy(() => import('./storefront/LegalPages'))

// Public (buyer) tree: no producer i18n, no AuthProvider.
export default function PublicApp() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/s/:slug" element={<PublicStorefront />} />
        <Route path="/s/:slug/impressum" element={<Legal kind="impressum" />} />
        <Route path="/s/:slug/datenschutz" element={<Legal kind="datenschutz" />} />
      </Routes>
    </BrowserRouter>
  )
}
