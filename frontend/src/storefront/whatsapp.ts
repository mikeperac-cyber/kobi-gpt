/** WhatsApp click-to-chat link; Turkish local formats become +90. Returns null when the number is unusable. */
export function waLink(phone: string | null | undefined, text: string): string | null {
  let d = (phone ?? '').replace(/\D/g, '')
  if (d.startsWith('00')) d = d.slice(2)
  else if (d.startsWith('0')) d = `90${d.slice(1)}`
  else if (d.length === 10 && d.startsWith('5')) d = `90${d}` // Turkish mobile without country code
  if (d.length < 11 || d.length > 15) return null
  return `https://wa.me/${d}?text=${encodeURIComponent(text)}`
}
