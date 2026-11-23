import { applyDraft, type Draft } from './productDraft.ts'

const blank = { name_tr: '', description_tr: ' ', material_or_ingredients: '', unit: 'kg', moq: '', unit_weight_kg: '', price_floor: '', photos: ['/p.webp'] }
const full: Draft = { name_tr: 'Pamuk Havlu', description_tr: 'Beyaz havlu.', material_or_ingredients: 'Pamuk', unit: 'adet' }
const fails: string[] = []
const eq = (name: string, got: unknown, want: unknown) => { if (JSON.stringify(got) !== JSON.stringify(want)) fails.push(`${name}: want ${JSON.stringify(want)}, got ${JSON.stringify(got)}`) }

let r = applyDraft(blank, full)
eq('fresh: all filled', r.filled, ['name_tr', 'description_tr', 'material_or_ingredients', 'unit'])
eq('fresh: values', [r.next.name_tr, r.next.description_tr, r.next.unit, r.next.photos], ['Pamuk Havlu', 'Beyaz havlu.', 'adet', ['/p.webp']])

r = applyDraft({ ...blank, name_tr: 'Benim adım' }, full)
eq('typed name kept', [r.next.name_tr, r.next.unit], ['Benim adım', 'kg'])
eq('typed name: others filled', r.filled, ['description_tr', 'material_or_ingredients'])

r = applyDraft(blank, { name_tr: null, description_tr: null, material_or_ingredients: null, unit: null })
eq('all null: nothing', r.filled, [])
eq('all null: unchanged', r.next, blank)

r = applyDraft(blank, { ...full, unit: 'ton' })
eq('bad unit ignored', [r.next.unit, r.filled.includes('unit')], ['kg', false])

if (fails.length) throw new Error(fails.join(' | '))
console.log('ok')
