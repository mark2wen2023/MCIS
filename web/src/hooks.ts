import { useCallback, useEffect, useState } from 'react'
import { onIdentityChange } from './api'

/** 拉取数据；身份（角色）切换时自动重新拉取。 */
export function useLoad<T>(loader: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)
  const reload = useCallback(() => setTick((t) => t + 1), [])
  useEffect(() => onIdentityChange(reload), [reload])
  useEffect(() => {
    let alive = true
    loader()
      .then((d) => { if (alive) { setData(d); setError(null) } })
      .catch((e: Error) => { if (alive) { setData(null); setError(e.message) } })
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tick, ...deps])
  return { data, error, reload }
}
