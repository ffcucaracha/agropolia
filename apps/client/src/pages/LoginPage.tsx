import { FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, deviceId } from '../api/client'
import { useAuthStore, type TokenPair } from '../auth/store'
import { Layout } from '../components/Layout'

type VerifyResult = { tokens?: TokenPair | null }

export function LoginPage() {
  const navigate = useNavigate()
  const setTokens = useAuthStore((state) => state.setTokens)
  const setActiveOrg = useAuthStore((state) => state.setActiveOrg)
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [stage, setStage] = useState<'phone' | 'code'>('phone')
  const [devCode, setDevCode] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  async function submitPhone(event: FormEvent) {
    event.preventDefault(); setPending(true); setError(null)
    try {
      const result = await api<{ dev_code?: string | null }>('/auth/otp/request', { method: 'POST', body: JSON.stringify({ phone, device_id: deviceId(), purpose: 'login' }) })
      setDevCode(result.dev_code ?? null); setStage('code')
    } catch (e) { setError(e instanceof Error ? e.message : 'Не удалось отправить код') }
    finally { setPending(false) }
  }

  async function submitCode(event: FormEvent) {
    event.preventDefault(); setPending(true); setError(null)
    try {
      const result = await api<VerifyResult>('/auth/otp/verify', { method: 'POST', body: JSON.stringify({ phone, device_id: deviceId(), purpose: 'login', code }) })
      if (!result.tokens) throw new Error('Сервер не вернул сессию')
      await setTokens(result.tokens)
      const me = await api<{ organization: { id: string } }>('/me')
      setActiveOrg(me.organization.id)
      navigate('/app', { replace: true })
    } catch (e) { setError(e instanceof Error ? e.message : 'Не удалось войти') }
    finally { setPending(false) }
  }

  return <Layout><section className="card"><Link className="back" to="/start">← Назад</Link><h1>Вход</h1>
    {stage === 'phone' ? <form onSubmit={submitPhone}><label>Телефон<input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+7 900 000-00-00" required /></label><button className="button primary" disabled={pending}>Получить код</button></form>
      : <form onSubmit={submitCode}><label>Код из SMS<input inputMode="numeric" pattern="[0-9]{6}" value={code} onChange={(e) => setCode(e.target.value)} required /></label>{devCode && <p className="dev-note">Dev OTP: {devCode}</p>}<button className="button primary" disabled={pending}>Войти</button></form>}
    {error && <p className="error">{error}</p>}
  </section></Layout>
}
