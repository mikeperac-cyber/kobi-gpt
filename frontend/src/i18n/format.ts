import i18n from './index'

const loc = () => (i18n.language === 'en' ? 'en-GB' : 'tr-TR')

export const formatDate = (d: Date | string | number) =>
  new Intl.DateTimeFormat(loc(), { dateStyle: 'medium' }).format(new Date(d))

export const formatNumber = (n: number) => new Intl.NumberFormat(loc()).format(n)

export const formatMoney = (n: number, cur: string) =>
  new Intl.NumberFormat(loc(), { style: 'currency', currency: cur }).format(n)

/** Parses user-typed numbers: "12,50" -> 12.5; in Turkish, "1.500" -> 1500. Returns null when not a number. */
export function parseLocaleNumber(raw: string): number | null {
  let s = raw.trim().replace(/\s/g, '')
  if (!s) return null
  if (s.includes(',')) s = s.replace(/\./g, '').replace(',', '.')
  else if (i18n.language === 'tr' && /^\d{1,3}(\.\d{3})+$/.test(s)) s = s.replace(/\./g, '')
  return /^-?\d+(\.\d+)?$/.test(s) ? Number(s) : null
}

/** Number -> input text with a decimal comma (parseLocaleNumber reads it back in either language). */
export const numToInput = (n: number | null | undefined) => (n == null ? '' : String(n).replace('.', ','))
