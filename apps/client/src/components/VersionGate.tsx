import { useEffect, useState, type PropsWithChildren } from 'react'
import { api, clientPlatform } from '../api/client'

type VersionPolicy = {
  state: 'ok' | 'soft_update' | 'force_update'
  recommended_version: string
  minimum_supported_version: string
}

export function VersionGate({ children }: PropsWithChildren) {
  const platform = clientPlatform()
  const [policy, setPolicy] = useState<VersionPolicy | null>(null)

  useEffect(() => {
    if (platform === 'web') return
    api<VersionPolicy>('/config/client-version').then(setPolicy).catch(() => setPolicy(null))
  }, [platform])

  if (policy?.state === 'force_update') {
    return <main className="shell"><section className="card"><h1>Требуется обновление</h1><p>Эта версия приложения больше не поддерживается. Установите актуальную версию.</p></section></main>
  }

  return <>{policy?.state === 'soft_update' && <div className="update-banner">Доступно обновление приложения.</div>}{children}</>
}
