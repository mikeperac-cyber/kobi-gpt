import { Component, type ErrorInfo, type ReactNode } from 'react'
import i18n from '../i18n'
import Button from './ui/Button'

export default class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  componentDidCatch(e: Error, info: ErrorInfo) {
    console.error(e, info.componentStack)
  }
  render() {
    if (!this.state.failed) return this.props.children
    return (
      <div role="alert" className="min-h-screen flex flex-col items-center justify-center gap-3 p-6 text-center">
        <h1 className="text-xl font-semibold">{i18n.t('errors.boundary_title')}</h1>
        <p>{i18n.t('errors.boundary_body')}</p>
        <Button onClick={() => this.setState({ failed: false })}>{i18n.t('common.retry')}</Button>
      </div>
    )
  }
}
