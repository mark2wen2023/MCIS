import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'
import { ApiError } from '../api'

interface ToastState { text: string; kind: 'ok' | 'err' }
const Ctx = createContext<(t: string, kind?: 'ok' | 'err') => void>(() => {})

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<ToastState | null>(null)
  const show = useCallback((text: string, kind: 'ok' | 'err' = 'ok') => {
    setToast({ text, kind })
    window.setTimeout(() => setToast((cur) => (cur?.text === text ? null : cur)), 3800)
  }, [])
  return (
    <Ctx.Provider value={show}>
      {children}
      {toast && <div className={`toast ${toast.kind}`}>{toast.text}</div>}
    </Ctx.Provider>
  )
}

export function useToast() {
  const show = useContext(Ctx)
  /** 执行写操作：成功提示 / 失败显示后端错误码与说明。 */
  const run = useCallback(
    async <T,>(fn: () => Promise<T>, okText: string): Promise<T | undefined> => {
      try {
        const r = await fn()
        show(okText, 'ok')
        return r
      } catch (e) {
        const msg = e instanceof ApiError ? `${e.code}：${e.message}` : String(e)
        show(msg, 'err')
        return undefined
      }
    },
    [show],
  )
  return { show, run }
}
