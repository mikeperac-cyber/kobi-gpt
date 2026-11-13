import type { InputHTMLAttributes } from 'react'

export default function Input({ className = '', ...p }: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...p} className={`w-full min-h-11 px-3 rounded-md border border-slate-300 bg-white focus:outline-2 focus:outline-navy ${className}`} />
}
