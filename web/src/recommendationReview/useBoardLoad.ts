import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { ApiError, getOperator, getRole } from '../api'

// Only for the keyed recommendation page. Reload invalidates before effect cleanup.
export function useLoad<T>(loader: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)
  const generation = useRef(0)
  const alive = useRef(true)
  const identity = useRef(JSON.stringify([getRole(), getOperator()]))
  const current = () => alive.current && identity.current === JSON.stringify([getRole(), getOperator()])
  useLayoutEffect(() => { alive.current = true; return () => { alive.current = false; generation.current++ } }, [])
  const reload = () => {
    if (!current()) return
    generation.current++; setLoading(true); setError(null); setTick(v => v + 1)
  }
  useEffect(() => {
    const version = generation.current
    let active = true
    const valid = () => active && current() && version === generation.current
    void (async () => {
      try {
        const result = await loader()
        if (valid()) { setData(result); setError(null); setLoading(false) }
      } catch (e) {
        if (valid()) {
          // Preserve the existing denial clearing behavior; never label denied data as a cache.
          if (e instanceof ApiError && e.status === 403) setData(null)
          setError((e as Error).message); setLoading(false)
        }
      }
    })()
    return () => { active = false }
  }, [tick])
  return { data, error, loading, reload }
}
