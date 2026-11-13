import i18n from './index'

const loc = () => (i18n.language === 'en' ? 'en-GB' : 'tr-TR')

export const formatDate = (d: Date | string | number) =>
  new Intl.DateTimeFormat(loc(), { dateStyle: 'medium' }).format(new Date(d))

export const formatNumber = (n: number) => new Intl.NumberFormat(loc()).format(n)

export const formatMoney = (n: number, cur: string) =>
  new Intl.NumberFormat(loc(), { style: 'currency', currency: cur }).format(n)
