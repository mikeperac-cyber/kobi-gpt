import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import tr from './tr.json'
import en from './en.json'

export const LANG_KEY = 'kobi_lang'

function stored(): 'tr' | 'en' {
  try {
    return localStorage.getItem(LANG_KEY) === 'en' ? 'en' : 'tr'
  } catch {
    return 'tr'
  }
}

i18n.use(initReactI18next).init({
  resources: { tr: { translation: tr }, en: { translation: en } },
  lng: stored(),
  fallbackLng: 'tr',
  interpolation: { escapeValue: false },
})

i18n.on('languageChanged', (l) => {
  document.documentElement.lang = l
  try {
    localStorage.setItem(LANG_KEY, l)
  } catch { /* storage unavailable */ }
})
document.documentElement.lang = i18n.language

export default i18n
