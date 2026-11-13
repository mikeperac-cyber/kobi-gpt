import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { api } from '../api/client'
import i18n from '../i18n'

export type Lang = 'tr' | 'en'
export interface User {
  id: string
  name: string
  email: string
  is_admin: boolean
  ui_language: Lang
  has_company: boolean
}

interface AuthCtx {
  user: User | null
  loading: boolean
  refresh(): Promise<User | null>
  login(email: string, pw: string): Promise<User>
  register(name: string, email: string, pw: string): Promise<User>
  logout(): Promise<void>
  setLanguage(lang: Lang): Promise<void>
}

const Ctx = createContext<AuthCtx | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const apply = (u: User) => {
    setUser(u)
    if (u.ui_language !== i18n.language) void i18n.changeLanguage(u.ui_language)
    return u
  }

  const refresh = useCallback(async () => {
    try {
      return apply(await api<User>('/api/auth/me'))
    } catch {
      setUser(null)
      return null
    }
  }, [])

  useEffect(() => {
    void refresh().finally(() => setLoading(false))
  }, [refresh])

  const value: AuthCtx = {
    user,
    loading,
    refresh,
    login: async (email, password) => apply(await api<User>('/api/auth/login', { method: 'POST', json: { email, password } })),
    register: async (name, email, password) => {
      const lang = i18n.language // new accounts default to tr server-side; keep the form's language
      await api('/api/auth/register', { method: 'POST', json: { name, email, password, kvkk_consent: true } })
      // Cookie is set now: load the user first so a failed language PATCH cannot strand the session.
      const u = (await refresh())!
      try {
        return apply(await api<User>('/api/auth/me', { method: 'PATCH', json: { ui_language: lang } }))
      } catch {
        return u
      }
    },
    logout: async () => {
      try {
        await api('/api/auth/logout', { method: 'POST' })
      } finally {
        setUser(null)
      }
    },
    setLanguage: async (lang) => {
      await i18n.changeLanguage(lang)
      if (user) {
        try {
          setUser(await api<User>('/api/auth/me', { method: 'PATCH', json: { ui_language: lang } }))
        } catch { /* UI already switched; server copy retried next change */ }
      }
    },
  }
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAuth() {
  const c = useContext(Ctx)
  if (!c) throw new Error('useAuth outside AuthProvider')
  return c
}
