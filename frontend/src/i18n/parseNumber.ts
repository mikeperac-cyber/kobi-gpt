// No imports on purpose: checked by backend/tests/test_parse_number.py via node (see parseNumber.check.ts).
const esc = (c: string) => `[${c}]`

/** Strict locale-aware number parse. tr: "," decimal, "." thousands; en: "." decimal, "," thousands.
 *  A thousands separator must be followed by exactly 3 digits per group and the first group cannot start with 0,
 *  so "0.500" (tr) and "1,5" (en) are rejected (null) instead of silently becoming a wrong number. */
export function parseNumber(raw: string, lang: string): number | null {
  const s = raw.replace(/\s/g, '')
  const dec = lang === 'en' ? '.' : ','
  const th = lang === 'en' ? ',' : '.'
  const plain = new RegExp(String.raw`^\d+(${esc(dec)}\d+)?$`)
  const grouped = new RegExp(String.raw`^[1-9]\d{0,2}(${esc(th)}\d{3})+(${esc(dec)}\d+)?$`)
  if (!plain.test(s) && !grouped.test(s)) return null
  return Number(s.split(th).join('').replace(dec, '.'))
}
