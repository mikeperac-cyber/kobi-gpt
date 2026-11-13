import i18n from './index'
import { parseNumber } from './parseNumber'

const loc = () => (i18n.language === 'en' ? 'en-GB' : 'tr-TR')

export const formatDate = (d: Date | string | number) =>
  new Intl.DateTimeFormat(loc(), { dateStyle: 'medium' }).format(new Date(d))

export const formatNumber = (n: number) => new Intl.NumberFormat(loc()).format(n)

export const formatMoney = (n: number, cur: string) =>
  new Intl.NumberFormat(loc(), { style: 'currency', currency: cur }).format(n)

/** Strict parse in the UI language (see parseNumber.ts); null when not a valid number. */
export const parseLocaleNumber = (raw: string): number | null => parseNumber(raw, i18n.language)

/** Number -> input text using the UI language's decimal separator. */
export const numToInput = (n: number | null | undefined) =>
  n == null ? '' : String(n).replace('.', i18n.language === 'en' ? '.' : ',')
