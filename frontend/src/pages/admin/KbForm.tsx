import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../../api/client'
import Button from '../../components/ui/Button'
import Field from '../../components/ui/Field'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import Textarea from '../../components/ui/Textarea'

export type Kind = 'rules' | 'incentives' | 'hs_codes'
export type Rec = Record<string, unknown> & { id: string; verified: boolean; last_verified: string | null }
type FieldDef = { name: string; type: 'text' | 'area' | 'list' | 'select' | 'bool'; options?: string[] }

const SECTORS = ['tekstil', 'gida', 'otomotiv_yan_sanayi', 'diger']
const T = (names: string[], type: FieldDef['type'] = 'text'): FieldDef[] => names.map((name) => ({ name, type }))

const FIELDS: Record<Kind, FieldDef[]> = {
  rules: [
    ...T(['id', 'title_tr', 'title_en']), ...T(['summary_tr', 'summary_en', 'what_to_do_tr', 'what_to_do_en'], 'area'),
    ...T(['documents_tr', 'documents_en', 'hs_prefixes', 'sectors'], 'list'), ...T(['country']),
    { name: 'channel', type: 'select', options: ['', 'b2b', 'b2c'] }, { name: 'structural_use', type: 'bool' },
    { name: 'side', type: 'select', options: ['TR', 'DEST'] },
    { name: 'level', type: 'select', options: ['zorunlu', 'koşullu', 'önerilen'] }, ...T(['source_url']),
  ],
  incentives: [
    ...T(['id', 'name_tr', 'name_en']), ...T(['summary_tr', 'summary_en', 'what_to_do_tr', 'what_to_do_en'], 'area'),
    { name: 'provider', type: 'select', options: ['Ticaret Bakanlığı', 'KOSGEB', 'Türk Eximbank', 'TİM'] },
    ...T(['stages', 'sectors'], 'list'), ...T(['source_url']),
  ],
  hs_codes: [
    ...T(['id']), { name: 'sector', type: 'select', options: SECTORS }, ...T(['description_tr', 'description_en']),
    ...T(['note_tr', 'note_en']),
  ],
}

// Form state is all strings; lists are `;`-joined, empty optional values become null.
const toState = (kind: Kind, r?: Rec) => Object.fromEntries(FIELDS[kind].map((f) => {
  const v = r?.[f.name]
  return [f.name, f.type === 'list' ? ((v as string[]) ?? []).join('; ') : f.type === 'bool' ? (v ? 'true' : '') : ((v as string) ?? (f.options?.[0] ?? ''))]
}))

const toBody = (kind: Kind, s: Record<string, string>) => Object.fromEntries(FIELDS[kind].map((f) => {
  const v = s[f.name].trim()
  if (f.type === 'list') return [f.name, v.split(';').map((x) => x.trim()).filter(Boolean)]
  if (f.type === 'bool') return [f.name, v === 'true' ? true : null]
  if (f.name === 'country' || f.name === 'channel') return [f.name, v || null]
  return [f.name, v]
}))

export default function KbForm({ kind, rec, onDone, onCancel }: { kind: Kind; rec?: Rec; onDone: () => void; onCancel: () => void }) {
  const { t } = useTranslation()
  const [s, setS] = useState(() => toState(kind, rec))
  const [err, setErr] = useState('')
  const [bad, setBad] = useState<string[]>([])
  const [busy, setBusy] = useState(false)

  async function save(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true); setErr(''); setBad([])
    try {
      await api(rec ? `/api/admin/kb/${kind}/${encodeURIComponent(rec.id)}` : `/api/admin/kb/${kind}`, { method: rec ? 'PUT' : 'POST', json: toBody(kind, s) })
      onDone()
    } catch (x) {
      setErr(t(x instanceof ApiError ? x.messageKey : 'errors.network'))
      if (x instanceof ApiError) setBad(x.fields)
    } finally { setBusy(false) }
  }

  return (
    <form onSubmit={save} className="space-y-3 bg-white border border-slate-200 rounded-md p-4">
      {FIELDS[kind].map((f) => {
        const label = t(`adminKb.fields.${f.name}`)
        const error = bad.some((b) => b === f.name || b.startsWith(`${f.name}.`)) ? t('adminKb.badFields', { f: label }) : undefined
        const common = { value: s[f.name], onChange: (e: React.ChangeEvent<HTMLInputElement & HTMLTextAreaElement & HTMLSelectElement>) => setS({ ...s, [f.name]: e.target.value }) }
        return (
          <Field key={f.name} label={label} error={error} hint={f.type === 'list' ? t('adminKb.listHint') : undefined}>
            {f.type === 'area' ? <Textarea {...common} />
              : f.type === 'select' ? <Select {...common}>{f.options!.map((o) => <option key={o} value={o}>{o || '—'}</option>)}</Select>
              : f.type === 'bool' ? <Select {...common}><option value="">—</option><option value="true">true</option></Select>
              : <Input {...common} disabled={f.name === 'id' && !!rec} />}
          </Field>
        )
      })}
      {err && <p role="alert" className="text-brand font-semibold">{err}</p>}
      <div className="flex gap-2">
        <Button type="submit" disabled={busy}>{t('adminKb.save')}</Button>
        <Button type="button" variant="secondary" onClick={onCancel}>{t('adminKb.cancel')}</Button>
      </div>
    </form>
  )
}
