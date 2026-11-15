// Buyer-facing mail text (not producer UI, so it lives outside the i18n JSON).
type Cover = { subject: string; body: (name: string) => string }

export const quoteCover: Record<'de' | 'en', Cover> = {
  de: {
    subject: 'Angebot',
    body: (name) => `Guten Tag${name ? ` ${name}` : ''},\n\nvielen Dank für Ihr Interesse. Anbei erhalten Sie unser Angebot als PDF.\nBei Fragen melde ich mich gern.\n\nMit freundlichen Grüßen`,
  },
  en: {
    subject: 'Quotation',
    body: (name) => `Dear${name ? ` ${name}` : ' Sir or Madam'},\n\nThank you for your interest. Please find our quotation attached as a PDF.\nI am happy to answer any questions.\n\nKind regards`,
  },
}

export const buyerLang = (country: string): 'de' | 'en' => (['DE', 'AT', 'CH'].includes((country || '').toUpperCase()) ? 'de' : 'en')
