import { lazy } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import PublicStorefront from './storefront/PublicStorefront'
import { STR } from './storefront/strings'

const Legal = lazy(() => import('./storefront/LegalPages'))

// Public (buyer) tree: no producer i18n, no AuthProvider.
export default function PublicApp() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/s/:slug" element={<PublicStorefront />} />
        <Route path="/s/:slug/impressum" element={<Legal kind="impressum" />} />
        <Route path="/s/:slug/datenschutz" element={<Legal kind="datenschutz" />} />
        <Route path="*" element={<PublicNotFound />} />
      </Routes>
    </BrowserRouter>
  )
}

/** Unknown public path: no language is known here, so say it in both buyer languages. */
function PublicNotFound() {
  return (
    <div className="p-8 text-center space-y-1">
      <p lang="de">{STR.de.notFound}</p>
      <p lang="en">{STR.en.notFound}</p>
    </div>
  )
}
