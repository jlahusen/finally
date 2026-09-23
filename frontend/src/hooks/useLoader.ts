import { useCallback, useEffect, useState } from 'react'

/** Loads data once on mount and exposes a `reload` to refetch on demand. */
export function useLoader<T>(load: () => Promise<T>, initial: T) {
  const [data, setData] = useState<T>(initial)
  const reload = useCallback(() => load().then(setData), [load])
  useEffect(() => {
    reload().catch(() => {})
  }, [reload])
  return [data, reload, setData] as const
}
