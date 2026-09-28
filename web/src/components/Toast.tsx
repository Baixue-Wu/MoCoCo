import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { useI18n } from '../i18n'

interface ToastItem {
  id: number
  text: string
  kind: 'info' | 'error'
}

interface ToastContextValue {
  show: (text: string, kind?: 'info' | 'error') => void
  showError: (err: unknown) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

let nextId = 1

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])

  const dismiss = useCallback((id: number) => {
    setItems((cur) => cur.filter((i) => i.id !== id))
  }, [])

  const show = useCallback(
    (text: string, kind: 'info' | 'error' = 'info') => {
      const id = nextId++
      setItems((cur) => [...cur, { id, text, kind }])
      setTimeout(() => dismiss(id), kind === 'error' ? 8000 : 4000)
    },
    [dismiss],
  )

  const showError = useCallback(
    (err: unknown) => {
      const text = err instanceof Error ? err.message : String(err)
      show(text, 'error')
    },
    [show],
  )

  const value = useMemo(() => ({ show, showError }), [show, showError])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-stack">
        {items.map((i) => (
          <ToastEntry key={i.id} item={i} onDismiss={() => dismiss(i.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

function ToastEntry({ item, onDismiss }: { item: ToastItem; onDismiss: () => void }) {
  const { t } = useI18n()
  return (
    <div className={`toast ${item.kind === 'error' ? 'toast-error' : ''}`}>
      <span>{item.text}</span>
      <button onClick={onDismiss} aria-label={t('toast.dismiss')}>
        ×
      </button>
    </div>
  )
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}
