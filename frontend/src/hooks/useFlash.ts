import { useEffect, useRef, useState } from 'react'

const FLASH_MS = 250

/** Returns `flash-up`/`flash-down` briefly after `price` changes, else ''. */
export function useFlash(price: number | null | undefined): string {
  const previous = useRef(price)
  const [flash, setFlash] = useState('')

  useEffect(() => {
    const before = previous.current
    previous.current = price
    if (price == null || before == null || price === before) return
    setFlash(price > before ? 'flash-up' : 'flash-down')
    const timer = setTimeout(() => setFlash(''), FLASH_MS)
    return () => clearTimeout(timer)
  }, [price])

  return flash
}
