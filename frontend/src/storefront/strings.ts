import type { Lang } from './types'

export type PublicCompany = {
  name: string | null; city: string | null; logo_url: string | null; founded_year: number | null
  contact: { phone: string | null; email: string | null; website: string | null }
  whatsapp: string | null // the number buyers may message; null hides the button
}
export type PublicLegal = {
  name: string | null; address: string | null; phone: string | null; email: string | null
  website: string | null; representative: string | null; register: string | null
}

export const COUNTRIES = ['DE', 'AT', 'CH', 'NL', 'FR', 'IT', 'ES', 'PL', 'BE', 'GB', 'US', 'TR']

export function countryName(code: string, lang: Lang): string {
  try { return new Intl.DisplayNames([lang], { type: 'region' }).of(code) ?? code } catch { return code }
}

type S = {
  products: string; about: string; whyUs: string; exportInfo: string; incoterms: string; leadTime: string
  samples: string; founded: string; team: string; certs: string; imprint: string; privacy: string
  back: string; langLabel: string; errTitle: string; errBody: string; retry: string; whatsapp: string; waText: string; notFound: string; loading: string; loadError: string
  rfq: {
    company: string; contact: string; email: string; country: string; products: string; quantity: string
    message: string; consent: string; consentLink: string; submit: string; sending: string
    thanksTitle: string; thanks: string; invalid: string; invalidCodes: Record<'gdpr_required' | 'invalid_email' | 'product_too_long', string>; tooMany: string; error: string; select: string
  }
  legal: Record<'provider' | 'address' | 'phone' | 'email' | 'web' | 'rep' | 'register', string>
  privacyBody: (c: { name: string; contact: string }) => { h: string; p: string }[]
}

export const STR: Record<Lang, S> = {
  de: {
    products: 'Produkte', about: 'Über uns', whyUs: 'Warum wir', exportInfo: 'Export & Lieferung',
    incoterms: 'Incoterms', leadTime: 'Lieferzeit', samples: 'Muster', founded: 'Gegründet', team: 'Mitarbeitende',
    certs: 'Zertifikate', imprint: 'Impressum', privacy: 'Datenschutzerklärung', back: 'Zurück zur Seite', langLabel: 'Sprache', errTitle: 'Etwas ist schiefgelaufen', errBody: 'Die Seite konnte nicht angezeigt werden.', retry: 'Erneut versuchen', whatsapp: 'Per WhatsApp schreiben', waText: 'Guten Tag, ich interessiere mich für Ihre Produkte ({url}).',
    notFound: 'Diese Seite existiert nicht oder ist nicht veröffentlicht.', loading: 'Wird geladen…',
    loadError: 'Die Seite konnte nicht geladen werden.',
    rfq: {
      company: 'Firma', contact: 'Ansprechpartner', email: 'E-Mail', country: 'Land', products: 'Produkte',
      quantity: 'Gewünschte Menge', message: 'Nachricht', select: 'Bitte wählen',
      consent: 'Ich stimme der Verarbeitung meiner Angaben zur Beantwortung dieser Anfrage zu.',
      consentLink: 'Datenschutzerklärung', submit: 'Anfrage senden', sending: 'Wird gesendet…',
      thanksTitle: 'Vielen Dank!', thanks: 'Ihre Anfrage wurde übermittelt. Wir melden uns in Kürze bei Ihnen.',
      invalid: 'Bitte prüfen Sie Ihre Angaben (E-Mail, Pflichtfelder, Einwilligung).',
      invalidCodes: {
        gdpr_required: 'Bitte stimmen Sie der Verarbeitung Ihrer Angaben zu.',
        invalid_email: 'Bitte geben Sie eine gültige E-Mail-Adresse ein.',
        product_too_long: 'Eine Produktangabe ist zu lang.',
      },
      tooMany: 'Zu viele Anfragen. Bitte versuchen Sie es später erneut.',
      error: 'Die Anfrage konnte nicht gesendet werden. Bitte versuchen Sie es später erneut.',
    },
    legal: {
      provider: 'Anbieter', address: 'Anschrift', phone: 'Telefon', email: 'E-Mail', web: 'Website',
      rep: 'Vertretungsberechtigte Person', register: 'Handelsregister',
    },
    privacyBody: ({ name, contact }) => [
      { h: 'Verantwortlicher', p: `${name}. Kontakt: ${contact}.` },
      { h: 'Zweck der Verarbeitung', p: 'Wenn Sie das Anfrageformular nutzen, verarbeiten wir die von Ihnen eingegebenen Daten (Firma, Name, E-Mail, Land, Produkte, Menge, Nachricht) ausschließlich, um Ihre Anfrage zu beantworten.' },
      { h: 'Rechtsgrundlage', p: 'Die Verarbeitung erfolgt auf Grundlage von Art. 6 Abs. 1 lit. b DSGVO (vorvertragliche Maßnahmen auf Ihre Anfrage) sowie Ihrer Einwilligung.' },
      { h: 'Speicherdauer', p: 'Wir speichern Ihre Daten nur so lange, wie es für die Bearbeitung Ihrer Anfrage und eine mögliche Geschäftsbeziehung erforderlich ist, sowie darüber hinaus, soweit gesetzliche Aufbewahrungspflichten bestehen.' },
      { h: 'Ihre Rechte', p: 'Sie haben das Recht auf Auskunft (Art. 15), Berichtigung (Art. 16), Löschung (Art. 17), Einschränkung der Verarbeitung (Art. 18), Datenübertragbarkeit (Art. 20) und Widerspruch (Art. 21) sowie auf Widerruf einer Einwilligung (Art. 7 Abs. 3). Zudem können Sie sich bei einer Datenschutz-Aufsichtsbehörde beschweren (Art. 77). Wenden Sie sich dazu an den oben genannten Verantwortlichen.' },
    ],
  },
  en: {
    products: 'Products', about: 'About us', whyUs: 'Why us', exportInfo: 'Export & delivery',
    incoterms: 'Incoterms', leadTime: 'Lead time', samples: 'Samples', founded: 'Founded', team: 'Team size',
    certs: 'Certifications', imprint: 'Legal notice', privacy: 'Privacy policy', back: 'Back to the site', langLabel: 'Language', errTitle: 'Something went wrong', errBody: 'The page could not be displayed.', retry: 'Try again', whatsapp: 'Message on WhatsApp', waText: 'Hello, I am interested in your products ({url}).',
    notFound: 'This page does not exist or is not published.', loading: 'Loading…',
    loadError: 'The page could not be loaded.',
    rfq: {
      company: 'Company', contact: 'Contact person', email: 'Email', country: 'Country', products: 'Products',
      quantity: 'Desired quantity', message: 'Message', select: 'Please select',
      consent: 'I agree to my details being processed to answer this request.',
      consentLink: 'Privacy policy', submit: 'Send request', sending: 'Sending…',
      thanksTitle: 'Thank you!', thanks: 'Your request has been sent. We will get back to you shortly.',
      invalid: 'Please check your entries (email, required fields, consent).',
      invalidCodes: {
        gdpr_required: 'Please consent to the processing of your details.',
        invalid_email: 'Please enter a valid email address.',
        product_too_long: 'A product entry is too long.',
      },
      tooMany: 'Too many requests. Please try again later.',
      error: 'Your request could not be sent. Please try again later.',
    },
    legal: {
      provider: 'Provider', address: 'Address', phone: 'Phone', email: 'Email', web: 'Website',
      rep: 'Authorised representative', register: 'Commercial register',
    },
    privacyBody: ({ name, contact }) => [
      { h: 'Controller', p: `${name}. Contact: ${contact}.` },
      { h: 'Purpose of processing', p: 'When you use the request form we process the data you enter (company, name, email, country, products, quantity, message) solely to answer your request.' },
      { h: 'Legal basis', p: 'Processing is based on Art. 6(1)(b) GDPR (steps prior to entering into a contract at your request) and on your consent.' },
      { h: 'Retention', p: 'We keep your data only as long as needed to handle your request and any resulting business relationship, and beyond that only where statutory retention duties apply.' },
      { h: 'Your rights', p: 'You have the right of access (Art. 15), rectification (Art. 16), erasure (Art. 17), restriction (Art. 18), data portability (Art. 20) and objection (Art. 21), and may withdraw consent at any time (Art. 7(3)). You may also lodge a complaint with a supervisory authority (Art. 77). Please contact the controller named above.' },
    ],
  },
}
