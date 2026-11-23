import type { ProductDraft } from './ProductForm'

export const UNITS = ['kg', 'adet', 'metre', 'koli'] as const

/** AI suggestion from `POST /api/products/draft` (null = the model was unsure). */
export type Draft = { name_tr: string | null; description_tr: string | null; material_or_ingredients: string | null; unit: string | null }
type TextKey = 'name_tr' | 'description_tr' | 'material_or_ingredients'
const TEXT: TextKey[] = ['name_tr', 'description_tr', 'material_or_ingredients']

/** Fill only blank fields: never overwrite what the producer typed. `unit` always has a default, so it is
 *  only taken for a fresh product (blank name). */
export function applyDraft(form: ProductDraft, d: Draft): { next: ProductDraft; filled: string[] } {
  const next = { ...form }
  const filled: string[] = []
  for (const k of TEXT) {
    const v = d[k]?.trim()
    if (v && !form[k].trim()) { next[k] = v; filled.push(k) }
  }
  if (!form.name_tr.trim() && d.unit && (UNITS as readonly string[]).includes(d.unit) && d.unit !== form.unit) {
    next.unit = d.unit
    filled.push('unit')
  }
  return { next, filled }
}
