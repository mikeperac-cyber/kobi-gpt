import { parseNumber as p } from './parseNumber.ts'

const cases: [string, string, number | null][] = [
  ['tr', '1,5', 1.5], ['tr', '12,50', 12.5], ['tr', '1.234,56', 1234.56], ['tr', '1.500', 1500], ['tr', '1500', 1500],
  ['tr', '0,5', 0.5], ['tr', '0.500', null], ['tr', '12.5', null], ['tr', '1.23', null], ['tr', '1.2345', null], ['tr', 'abc', null], ['tr', '', null],
  ['en', '1,500', 1500], ['en', '1,234.56', 1234.56], ['en', '12.5', 12.5], ['en', '1500', 1500], ['en', '1,5', null], ['en', '0,500', null], ['en', '1,23', null],
]
const bad = cases.filter(([lang, input, want]) => p(input, lang) !== want).map(([l, i, w]) => `${l} "${i}": want ${w}, got ${p(i, l)}`)
if (bad.length) throw new Error(bad.join(' | '))
console.log('ok', cases.length)
