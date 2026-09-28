import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import en from './en.json'
import zh from './zh.json'

export type UiLang = 'en' | 'zh'

const dictionaries: Record<UiLang, Record<string, string>> = { en, zh }

const STORAGE_KEY = 'mococo.ui_lang'

function readStored(): UiLang {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (v === 'en' || v === 'zh') return v
  } catch {
    /* ignore */
  }
  return 'en'
}

interface I18nContextValue {
  lang: UiLang
  setLang: (l: UiLang) => void
  t: (key: string, vars?: Record<string, string | number>) => string
}

const I18nContext = createContext<I18nContextValue | null>(null)

function format(template: string, vars?: Record<string, string | number>): string {
  if (!vars) return template
  return template.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? String(vars[k]) : `{${k}}`))
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<UiLang>(readStored)

  const setLang = useCallback((l: UiLang) => {
    setLangState(l)
    try {
      localStorage.setItem(STORAGE_KEY, l)
    } catch {
      /* ignore */
    }
  }, [])

  const t = useCallback(
    (key: string, vars?: Record<string, string | number>) => {
      const dict = dictionaries[lang]
      const template = dict[key] ?? dictionaries.en[key] ?? key
      return format(template, vars)
    },
    [lang],
  )

  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t])
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used within I18nProvider')
  return ctx
}
