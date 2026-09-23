import type { ReactNode } from 'react'

interface Props {
  title: string
  aside?: ReactNode
  className?: string
  children: ReactNode
}

/** Bordered terminal pane with a compact title bar. */
export function Panel({ title, aside, className = '', children }: Props) {
  return (
    <section className={`flex min-h-0 flex-col border border-line bg-panel ${className}`}>
      <header className="flex h-7 shrink-0 items-center justify-between border-b border-line px-2">
        <h2 className="text-[12px] font-medium text-muted">{title}</h2>
        {aside}
      </header>
      <div className="min-h-0 flex-1">{children}</div>
    </section>
  )
}
