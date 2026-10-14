import { FormEvent, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, deviceId } from '../api/client'
import { useAuthStore, type TokenPair } from '../auth/store'
import { Layout } from '../components/Layout'

type VerifyResult = { tokens?: TokenPair | null }
type AuthConfig = { methods: string[]; otp_ttl_seconds: number; otp_resend_cooldown_seconds: number }

export function LoginPage() {
  const navigate = useNavigate()
  const setTokens = useAuthStore((state) => state.setTokens)
  const setActiveOrg = useAuthStore((state) => state.setActiveOrg)
  const [method, setMethod] = useState('email')
  const [methods, setMethods] = useState<string[]>(['email'])
  const [identifier, setIdentifier] = useState('')
  const [code, setCode] = useState('')
  const [stage, setStage] = useState<'identifier' | 'code'>('identifier')
  const [devCode, setDevCode] = useState<string | null>(null)
  const [resendAvailableIn, setResendAvailableIn] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  useEffect(() => {
    api<AuthConfig>('/config/auth').then((cfg) => {
      if (cfg.methods.length) {
        setMethods(cfg.methods)
        setMethod(cfg.methods[0])
      }
    }).catch(() => undefined)
  }, [])

  useEffect(() => {
    if (resendAvailableIn <= 0) return
    const timer = window.setInterval(() => {
      setResendAvailableIn((value) => Math.max(0, value - 1))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [resendAvailableIn])

  async function requestOtp() {
    const result = await api<{ dev_code?: string | null; resend_available_in: number }>('/auth/otp/request', {
      method: 'POST',
      body: JSON.stringify({ method, identifier, device_id: deviceId(), purpose: 'login' }),
    })
    setDevCode(result.dev_code ?? null)
    setResendAvailableIn(result.resend_available_in)
  }

  async function submitIdentifier(event: FormEvent) {
    event.preventDefault(); setPending(true); setError(null)
    try {
      await requestOtp()
      setStage('code')
    } catch (e) { setError(e instanceof Error ? e.message : 'Не удалось отправить код') }
    finally { setPending(false) }
  }

  async function resendOtp() {
    setPending(true); setError(null)
    try { await requestOtp() }
    catch (e) { setError(e instanceof Error ? e.message : 'Не удалось повторно отправить код') }
    finally { setPending(false) }
  }

  async function submitCode(event: FormEvent) {
    event.preventDefault(); setPending(true); setError(null)
    try {
      const result = await api<VerifyResult>('/auth/otp/verify', {
        method: 'POST',
        body: JSON.stringify({ method, identifier, device_id: deviceId(), purpose: 'login', code }),
      })
      if (!result.tokens) throw new Error('Сервер не вернул сессию')
      await setTokens(result.tokens)
      const me = await api<{ organization: { id: string } }>('/me')
      setActiveOrg(me.organization.id)
      navigate('/app', { replace: true })
    } catch (e) { setError(e instanceof Error ? e.message : 'Не удалось войти') }
    finally { setPending(false) }
  }

  const label = method === 'email' ? 'Email' : 'Телефон'
  const inputType = method === 'email' ? 'email' : 'tel'

  return <Layout><section className="card"><Link className="back" to="/start">← Назад</Link><h1>Вход</h1>
    {stage === 'identifier' ? <form onSubmit={submitIdentifier}>
      {methods.length > 1 && <label>Способ входа<select value={method} onChange={(e) => setMethod(e.target.value)}>{methods.map((item) => <option key={item} value={item}>{item === 'email' ? 'Email' : 'Телефон'}</option>)}</select></label>}
      <label>{label}<input type={inputType} value={identifier} onChange={(e) => setIdentifier(e.target.value)} placeholder={method === 'email' ? 'user@example.ru' : '+7 900 000-00-00'} required /></label>
      <button className="button primary" disabled={pending}>Получить код</button>
    </form>
      : <form onSubmit={submitCode}>
        <label>Код из письма<input inputMode="numeric" pattern="[0-9]{6}" value={code} onChange={(e) => setCode(e.target.value)} required /></label>
        {devCode && <p className="dev-note">Dev OTP: {devCode}</p>}
        <button className="button primary" disabled={pending}>Войти</button>
        <button type="button" className="button secondary" disabled={pending || resendAvailableIn > 0} onClick={() => void resendOtp()}>
          {resendAvailableIn > 0 ? `Отправить повторно через ${resendAvailableIn} с` : 'Отправить код повторно'}
        </button>
      </form>}
    {error && <p className="error">{error}</p>}
  </section></Layout>
}
