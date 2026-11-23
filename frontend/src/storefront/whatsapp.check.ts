import { waLink } from './whatsapp.ts'

const T = 'Guten Tag & mehr'
const enc = 'Guten%20Tag%20%26%20mehr'
const tr = `https://wa.me/905321234567?text=${enc}`
const cases: [string | null | undefined, string | null][] = [
  ['0532 123 45 67', tr], ['+90 (532) 123-45-67', tr], ['0090 532 123 45 67', tr], ['5321234567', tr],
  ['+49 30 1234567', `https://wa.me/49301234567?text=${enc}`],
  ['abc', null], ['', null], [null, null], [undefined, null], ['123', null],
]
const bad = cases.filter(([p, want]) => waLink(p, T) !== want).map(([p, w]) => `"${p}": want ${w}, got ${waLink(p, T)}`)
if (bad.length) throw new Error(bad.join(' | '))
console.log('ok', cases.length)
