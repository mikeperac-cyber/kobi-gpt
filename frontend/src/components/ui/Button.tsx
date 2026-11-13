import type { ButtonHTMLAttributes } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost'
const styles: Record<Variant, string> = {
  primary: 'bg-brand text-white hover:bg-red-800',
  secondary: 'bg-white text-navy border border-slate-300 hover:bg-slate-100',
  ghost: 'text-navy hover:bg-slate-100',
}

export default function Button({ variant = 'primary', className = '', ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      {...p}
      className={`min-h-11 px-4 rounded-md font-semibold disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-navy ${styles[variant]} ${className}`}
    />
  )
}
