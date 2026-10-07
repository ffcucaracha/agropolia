import { FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, deviceId } from '../api/client'
import { useAuthStore, type TokenPair } from '../auth/store'
import { Layout } from '../components/Layout'

export function RegisterPage() {
  const navigate = useNavigate()
  const setTokens = useAuthStore((state) => state.setTokens)
  const setActiveOrg = useAuthStore((state) => state.setActiveOrg)
  const [stage, setStage] = useState<'phone' | 'code' | 'details'>('phone')
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [devCode, setDevCode] = useState<string | null>(null)
  const [registrationToken, setRegistrationToken] = useState('')
  const [name, setName] = useState('')
  const [orgType, setOrgType] = useState<'SHO' | 'KFH'>('KFH')
  const [inn, setInn] = useState('')
  const [orgName, setOrgName] = useState('')
  const [consent, setConsent] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  async function requestOtp(event: FormEvent) {
    event.preventDefault(); setPending(true); setError(null)
    try {
      const result = await api<{ dev_code?: string | null }>('/auth/otp/request', { method: 'POST', body: JSON.stringify({ phone, device_id: deviceId(), purpose: 'register' }) })
      setDevCode(result.dev_code ?? null); setStage('code')
    } catch (e) { setError(e instanceof Error ? e.message : 'Не удалось отправить код') }
    finally { setPending(false) }
  }

  async function verifyOtp(event: FormEvent) {
    event.preventDefault(); setPending(true); setError(null)
    try {
      const result = await api<{ registration_token?: string | null }>('/auth/otp/verify', { method: 'POST', body: JSON.stringify({ phone, device_id: deviceId(), purpose: 'register', code }) })
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

  return <Layout><section className="card"><Link className="back" to="/start">← Назад</Link><h1>Регистрация</h1>
    {stage === 'phone' && <form onSubmit={requestOtp}><label>Телефон<input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+7 900 000-00-00" required /></label><button className="button primary" disabled={pending}>Получить код</button></form>}
    {stage === 'code' && <form onSubmit={verifyOtp}><label>Код из SMS<input inputMode="numeric" pattern="[0-9]{6}" value={code} onChange={(e) => setCode(e.target.value)} required /></label>{devCode && <p className="dev-note">Dev OTP: {devCode}</p>}<button className="button primary" disabled={pending}>Продолжить</button></form>}
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
