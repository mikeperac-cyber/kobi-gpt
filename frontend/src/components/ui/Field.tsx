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
      {cloneElement(children, { id, 'aria-invalid': !!error, 'aria-describedby': `${id}-d` })}
      <p id={`${id}-d`} className={`text-sm ${error ? 'text-brand' : 'text-slate-600'}`}>{error ?? hint}</p>
    </div>
  )
}
