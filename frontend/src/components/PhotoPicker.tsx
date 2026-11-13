import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../api/client'
import Button from './ui/Button'

/** Photo list with upload, remove and up/down reordering (buttons, so it works by keyboard and on touch). */
export default function PhotoPicker({ urls, max = 6, prefix = 'products', onChange }: {
  urls: string[]
  max?: number
  prefix?: 'products' | 'logos'
  onChange(urls: string[]): void
}) {
  const { t } = useTranslation()
  const input = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const pick = async (files: FileList | null) => {
    if (!files?.length) return
    setBusy(true)
    setErr('')
    let next = urls
    for (const file of Array.from(files).slice(0, max - urls.length)) {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('prefix', prefix)
      try {
        const { url } = await api<{ url: string }>('/api/uploads/image', { method: 'POST', body: fd })
        next = [...next, url]
        onChange(next)
      } catch (x) {
        setErr(t(x instanceof ApiError ? x.messageKey : 'errors.network'))
        break
      }
    }
    setBusy(false)
    if (input.current) input.current.value = ''
  }
  const move = (i: number, d: number) => {
    const a = [...urls]
    ;[a[i], a[i + d]] = [a[i + d], a[i]]
    onChange(a)
  }

  return (
    <div className="space-y-2">
      {urls.length > 0 && (
        <ul className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {urls.map((u, i) => (
            <li key={u} className="border border-slate-200 rounded-md p-2 bg-white space-y-2">
              <img src={u} alt={t('photos.alt', { n: i + 1 })} className="w-full aspect-square object-cover rounded" />
              <div className="flex gap-1">
                <Button type="button" variant="secondary" className="px-0 flex-1" disabled={i === 0} onClick={() => move(i, -1)} aria-label={t('photos.moveUp', { n: i + 1 })}>↑</Button>
                <Button type="button" variant="secondary" className="px-0 flex-1" disabled={i === urls.length - 1} onClick={() => move(i, 1)} aria-label={t('photos.moveDown', { n: i + 1 })}>↓</Button>
                <Button type="button" variant="secondary" className="px-0 flex-1" onClick={() => onChange(urls.filter((x) => x !== u))} aria-label={t('photos.remove', { n: i + 1 })}>✕</Button>
              </div>
            </li>
          ))}
        </ul>
      )}
      {urls.length < max && (
        <>
          <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" multiple={max > 1} className="sr-only"
            onChange={(e) => void pick(e.target.files)} aria-label={t('photos.add')} tabIndex={-1} />
          <Button type="button" variant="secondary" disabled={busy} onClick={() => input.current?.click()}>
            {busy ? t('photos.uploading') : t('photos.add')}
          </Button>
        </>
      )}
      <p className="text-sm text-slate-600">{t('photos.hint', { max })}</p>
      {err && <p role="alert" className="text-sm text-brand font-semibold">{err}</p>}
    </div>
  )
}
