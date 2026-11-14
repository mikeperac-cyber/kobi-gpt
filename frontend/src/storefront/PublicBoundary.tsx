import { Component, type ReactNode } from 'react'
import { STR } from './strings'

// Wraps the whole app: no producer i18n here, copy is DE/EN from ?lang= (default de).
export default class PublicBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  componentDidCatch(e: Error) { console.error(e) }
  render() {
    if (!this.state.failed) return this.props.children
    const lang = new URLSearchParams(location.search).get('lang') === 'en' ? 'en' : 'de'
    const s = STR[lang]
    return (
      <div role="alert" lang={lang} className="min-h-screen flex flex-col items-center justify-center gap-3 p-6 text-center">
        <h1 className="text-xl font-semibold">{s.errTitle}</h1>
        <p>{s.errBody}</p>
        <button onClick={() => location.reload()} className="rounded-md px-5 py-3 min-h-11 font-semibold bg-slate-900 text-white">{s.retry}</button>
      </div>
    )
  }
}
