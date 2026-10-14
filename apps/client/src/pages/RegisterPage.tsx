import { FormEvent, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, deviceId } from '../api/client'
import { useAuthStore, type TokenPair } from '../auth/store'
import { Layout } from '../components/Layout'

type AuthConfig = { methods: string[]; otp_ttl_seconds: number; otp_resend_cooldown_seconds: number }

export function RegisterPage() {
  const navigate = useNavigate()
  const setTokens = useAuthStore((state) => state.setTokens)
  const setActiveOrg = useAuthStore((state) => state.setActiveOrg)
  const [stage, setStage] = useState<'identifier' | 'code' | 'details'>('identifier')
  const [method, setMethod] = useState('email')
  const [methods, setMethods] = useState<string[]>(['email'])
  const [identifier, setIdentifier] = useState('')
  const [code, setCode] = useState('')
  const [devCode, setDevCode] = useState<string | null>(null)
  const [resendAvailableIn, setResendAvailableIn] = useState(0)
  const [registrationToken, setRegistrationToken] = useState('')
  const [name, setName] = useState('')
  const [orgType, setOrgType] = useState<'SHO' | 'KFH'>('KFH')
  const [inn, setInn] = useState('')
  const [orgName, setOrgName] = useState('')
  const [consent, setConsent] = useState(false)
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
    const timer = window.setInterval(() => setResendAvailableIn((value) => Math.max(0, value - 1)), 1000)
    return () => window.clearInterval(timer)
  }, [resendAvailableIn])

  async function requestOtp() {
    const result = await api<{ dev_code?: string | null; resend_available_in: number }>('/auth/otp/request', {
      method: 'POST',
      body: JSON.stringify({ method, identifier, device_id: deviceId(), purpose: 'register' }),
    })
    setDevCode(result.dev_code ?? null)
    setResendAvailableIn(result.resend_available_in)
  }

  async function submitIdentifier(event: FormEvent) {
    event.preventDefault(); setPending(true); setError(null)
    try { await requestOtp(); setStage('code') }
    catch (e) { setError(e instanceof Error ? e.message : 'Не удалось отправить код') }
    finally { setPending(false) }
  }

  async function resendOtp() {
    setPending(true); setError(null)
    try { await requestOtp() }
    catch (e) { setError(e instanceof Error ? e.message : 'Не удалось повторно отправить код') }
    finally { setPending(false) }
  }

  async function verifyOtp(event: FormEvent) {
    event.preventDefault(); setPending(true); setError(null)
    try {
      const result = await api<{ registration_token?: string | null }>('/auth/otp/verify', {
        method: 'POST',
        body: JSON.stringify({ method, identifier, device_id: deviceId(), purpose: 'register', code }),
      })
      if (!result.registration_token) throw new Error('Сервер не подтвердил регистрацию')
      setRegistrationToken(result.registration_token); setStage('details')
    } catch (e) { setError(e instanceof Error ? e.message : 'Не удалось подтвердить код') }
    finally { setPending(false) }
  }

  async function register(event: FormEvent) {
    event.preventDefault(); setPending(true); setError(null)
    try {
      const tokens = await api<TokenPair>('/auth/register', { method: 'POST', body: JSON.stringify({
        registration_token: registrationToken,
        name,
        organization_type: orgType,
        organization_inn: inn,
        organization_name: orgName,
        consent_version: 'i0-pd-1',
        consent_accepted: consent,
      }) })
      await setTokens(tokens)
      const me = await api<{ organization: { id: string } }>('/me')
      setActiveOrg(me.organization.id)
      navigate('/app', { replace: true })
    } catch (e) { setError(e instanceof Error ? e.message : 'Не удалось зарегистрироваться') }
    finally { setPending(false) }
  }

  const label = method === 'email' ? 'Email' : 'Телефон'
  const inputType = method === 'email' ? 'email' : 'tel'

  return <Layout><section className="card"><Link className="back" to="/start">← Назад</Link><h1>Регистрация</h1>
    {stage === 'identifier' && <form onSubmit={submitIdentifier}>
      {methods.length > 1 && <label>Способ регистрации<select value={method} onChange={(e) => setMethod(e.target.value)}>{methods.map((item) => <option key={item} value={item}>{item === 'email' ? 'Email' : 'Телефон'}</option>)}</select></label>}
      <label>{label}<input type={inputType} value={identifier} onChange={(e) => setIdentifier(e.target.value)} placeholder={method === 'email' ? 'user@example.ru' : '+7 900 000-00-00'} required /></label>
      <button className="button primary" disabled={pending}>Получить код</button>
    </form>}
    {stage === 'code' && <form onSubmit={verifyOtp}>
      <label>Код из письма<input inputMode="numeric" pattern="[0-9]{6}" value={code} onChange={(e) => setCode(e.target.value)} required /></label>
      {devCode && <p className="dev-note">Dev OTP: {devCode}</p>}
      <button className="button primary" disabled={pending}>Продолжить</button>
      <button type="button" className="button secondary" disabled={pending || resendAvailableIn > 0} onClick={() => void resendOtp()}>
        {resendAvailableIn > 0 ? `Отправить повторно через ${resendAvailableIn} с` : 'Отправить код повторно'}
      </button>
    </form>}
    {stage === 'details' && <form onSubmit={register}>
      <label>Имя<input value={name} onChange={(e) => setName(e.target.value)} required /></label>
      <label>Тип хозяйства<select value={orgType} onChange={(e) => setOrgType(e.target.value as 'SHO' | 'KFH')}><option value="KFH">КФХ</option><option value="SHO">СХО</option></select></label>
      <label>ИНН<input inputMode="numeric" value={inn} onChange={(e) => setInn(e.target.value)} required /></label>
      <label>Название хозяйства<input value={orgName} onChange={(e) => setOrgName(e.target.value)} required /></label>
      <label className="checkbox"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} required />Согласен на обработку персональных данных</label>
      <button className="button primary" disabled={pending}>Создать хозяйство</button>
    </form>}
    {error && <p className="error">{error}</p>}
  </section></Layout>
}
