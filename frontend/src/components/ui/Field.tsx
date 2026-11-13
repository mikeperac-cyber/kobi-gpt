import { useId, cloneElement, type ReactElement, type ReactNode } from 'react'

export default function Field({ label, hint, error, children }: {
  label: string
  hint?: ReactNode
  error?: string
  children: ReactElement<Record<string, unknown>>
}) {
  const id = useId()
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-sm font-semibold">{label}</label>
      {cloneElement(children, { id, 'aria-invalid': !!error, 'aria-describedby': error || hint ? `${id}-d` : undefined })}
      <div id={`${id}-d`} className="text-sm">
        {hint && <p className="text-slate-600">{hint}</p>}
        {error && <p role="alert" className="text-brand font-semibold">{error}</p>}
      </div>
    </div>
  )
}
