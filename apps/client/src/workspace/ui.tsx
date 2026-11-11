import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

export function PageHead({ title, action, subtitle }: { title: string; action?: { to: string; text: string }; subtitle?: string }) {
  return <div className="page-head"><div><h1>{title}</h1>{subtitle && <p className="muted">{subtitle}</p>}</div>
    {action && <Link className="button primary" to={action.to}>{action.text}</Link>}
  </div>
}

export function StateMessage({ children }: { children: ReactNode }) {
  return <section className="workspace-panel"><p className="muted">{children}</p></section>
}

export function ErrorMessage({ error }: { error: unknown }) {
  return <p role="alert" className="error">{error instanceof Error ? error.message : 'Произошла ошибка'}</p>
}

export function PendingTag({ pending }: { pending?: boolean }) {
  return pending ? <span className="pending-tag">Ожидает синхронизации</span> : null
}

export function formatDate(value: string | null | undefined) {
  if (!value) return 'Не задана'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('ru-RU', { dateStyle: 'short', timeStyle: 'short' })
}

export function BackLink({ to, text = 'Назад' }: { to: string; text?: string }) {
  return <Link className="back" to={to}>← {text}</Link>
}
