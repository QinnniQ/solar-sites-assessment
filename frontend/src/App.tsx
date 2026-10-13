import { useEffect, useState, type FormEvent } from 'react'
import { api, ApiError, type Battery, type Production, type Site, type SiteInput } from './api'

const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const whole = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 })
const decimal = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 2 })

function kwh(value: number) {
  return whole.format(value) + ' kWh'
}

function errorText(error: unknown) {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.'
}

function Brand() {
  return (
    <div className="brand" aria-label="Solar Sites">
      <span className="brand-mark" aria-hidden="true"><span /></span>
      <span>solar<span className="brand-light">sites</span><small>ADVISOR WORKSPACE</small></span>
    </div>
  )
}

function AuthScreen({ onAuthenticated }: { onAuthenticated: (email: string) => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const result = await api<{ email: string }>(
        mode === 'register' ? '/api/register' : '/api/login',
        { method: 'POST', body: JSON.stringify({ email, password }) }
      )
      onAuthenticated(result.email)
    } catch (reason) {
      setError(errorText(reason))
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="auth-layout">
      <section className="auth-aside">
        <Brand />
        <div className="auth-story">
          <div className="eyebrow light">A CLEARER VIEW OF SOLAR</div>
          <h1>Better decisions begin with better estimates.</h1>
          <p>Bring every client site, production estimate, and battery scenario into one considered workspace.</p>
        </div>
        <div className="auth-aside-footer">Powered by European Commission PVGIS data</div>
      </section>
      <section className="auth-main">
        <div className="auth-card">
          <div className="eyebrow">WELCOME TO SOLAR SITES</div>
          <h2>{mode === 'login' ? 'Sign in to your workspace' : 'Create your advisor account'}</h2>
          <p className="muted">
            {mode === 'login'
              ? 'Your sites and estimates are ready when you are.'
              : 'Start with a secure account. Your client sites stay private to you.'}
          </p>
          <form onSubmit={submit} className="form-stack">
            <label>
              <span>Email address</span>
              <input
                type="email"
                autoComplete="email"
                value={email}
                onChange={event => setEmail(event.target.value)}
                required
                autoFocus
              />
            </label>
            <label>
              <span>Password</span>
              <input
                type="password"
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                minLength={mode === 'register' ? 8 : undefined}
                value={password}
                onChange={event => setPassword(event.target.value)}
                required
              />
              {mode === 'register' && <small>At least 8 characters.</small>}
            </label>
            {error && <div className="alert error" role="alert">{error}</div>}
            <button className="button primary full" type="submit" disabled={busy}>
              {busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
              {!busy && <span aria-hidden="true">↗</span>}
            </button>
          </form>
          <p className="auth-switch">
            {mode === 'login' ? 'New to Solar Sites?' : 'Already have an account?'}{' '}
            <button
              className="text-button"
              onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}
            >
              {mode === 'login' ? 'Create an account' : 'Sign in'}
            </button>
          </p>
        </div>
      </section>
    </main>
  )
}

function SiteForm({
  site,
  onSave,
  onCancel
}: {
  site: Site | null
  onSave: (input: SiteInput) => Promise<void>
  onCancel: () => void
}) {
  const [clientName, setClientName] = useState(site?.clientName ?? '')
  const [address, setAddress] = useState(site?.address ?? '')
  const [latitude, setLatitude] = useState(site?.latitude?.toString() ?? '')
  const [longitude, setLongitude] = useState(site?.longitude?.toString() ?? '')
  const [roofAreaM2, setRoofAreaM2] = useState(site?.roofAreaM2?.toString() ?? '')
  const [peakKwp, setPeakKwp] = useState(site?.peakKwp?.toString() ?? '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [fields, setFields] = useState<Record<string, string>>({})

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setFields({})
    try {
      await onSave({
        clientName,
        address,
        latitude: Number(latitude),
        longitude: Number(longitude),
        roofAreaM2: roofAreaM2.trim() === '' ? null : Number(roofAreaM2),
        peakKwp: Number(peakKwp)
      })
    } catch (reason) {
      setError(errorText(reason))
      if (reason instanceof ApiError) setFields(reason.fields)
    } finally {
      setBusy(false)
    }
  }

  const fieldError = (name: string) => fields[name] && <small className="field-error">{fields[name]}</small>

  return (
    <section className="content-page narrow">
      <button className="back-link" onClick={onCancel}>← Back to {site ? 'site' : 'sites'}</button>
      <div className="page-heading">
        <div>
          <div className="eyebrow">CLIENT SITE</div>
          <h1>{site ? 'Edit site details' : 'Add a new site'}</h1>
          <p>Keep the inputs precise. We use coordinates and panel capacity for the solar estimate.</p>
        </div>
      </div>
      <form className="form-card" onSubmit={submit}>
        <div className="form-section-title">Location & client</div>
        <div className="form-grid">
          <label className="span-two">
            <span>Client name <b>*</b></span>
            <input value={clientName} onChange={event => setClientName(event.target.value)} maxLength={160} required placeholder="e.g. Van Dijk family" />
            {fieldError('clientName')}
          </label>
          <label className="span-two">
            <span>Address <b>*</b></span>
            <input value={address} onChange={event => setAddress(event.target.value)} maxLength={300} required placeholder="Street and city" />
            {fieldError('address')}
          </label>
          <label>
            <span>Latitude <b>*</b></span>
            <input type="number" step="any" min="-90" max="90" value={latitude} onChange={event => setLatitude(event.target.value)} required placeholder="52.08" />
            {fieldError('latitude')}
          </label>
          <label>
            <span>Longitude <b>*</b></span>
            <input type="number" step="any" min="-180" max="180" value={longitude} onChange={event => setLongitude(event.target.value)} required placeholder="4.31" />
            {fieldError('longitude')}
          </label>
        </div>
        <div className="form-section-title second">Solar system</div>
        <div className="form-grid">
          <label>
            <span>Panel capacity <b>*</b></span>
            <div className="input-unit"><input type="number" step="any" min="0.001" value={peakKwp} onChange={event => setPeakKwp(event.target.value)} required placeholder="5" /><em>kWp</em></div>
            {fieldError('peakKwp')}
          </label>
          <label>
            <span>Roof area <span className="optional">optional</span></span>
            <div className="input-unit"><input type="number" step="any" min="0.001" value={roofAreaM2} onChange={event => setRoofAreaM2(event.target.value)} placeholder="48" /><em>m²</em></div>
            {fieldError('roofAreaM2')}
          </label>
        </div>
        <p className="form-note">Roof area is stored for reference. The estimate uses the capacity you enter; it does not verify panel fit.</p>
        {error && <div className="alert error" role="alert">{error}</div>}
        <div className="form-actions">
          <button type="button" className="button subtle" onClick={onCancel}>Cancel</button>
          <button type="submit" className="button primary" disabled={busy}>{busy ? 'Saving…' : site ? 'Save changes' : 'Create site'} <span aria-hidden="true">↗</span></button>
        </div>
      </form>
    </section>
  )
}

function ProductionCard({ data, error, loading, retry }: {
  data: Production | null
  error: string
  loading: boolean
  retry: () => void
}) {
  if (loading) return <section className="panel loading-panel" aria-live="polite"><div className="spinner" />Calculating solar production from PVGIS…</section>
  if (error) return <section className="panel"><div className="eyebrow">SOLAR PRODUCTION</div><div className="alert error" role="alert">{error}</div><button className="button subtle" onClick={retry}>Try again</button></section>
  if (!data) return null
  const maximum = Math.max(...data.monthlyKwh.map(item => item.kwh), 1)
  return (
    <section className="panel production-panel">
      <div className="panel-header">
        <div><div className="eyebrow">SOLAR PRODUCTION</div><h2>Estimated generation</h2></div>
        <span className="data-badge"><span /> PVGIS estimate</span>
      </div>
      <div className="big-stat">{whole.format(data.yearlyKwh)} <span>kWh / year</span></div>
      <div className="chart-heading"><span>Monthly production</span><span>kWh</span></div>
      <div className="bar-chart" aria-hidden="true">
        {data.monthlyKwh.map(item => (
          <div className="bar-column" key={item.month}>
            <div className="bar-track"><div className="bar" style={{ height: String(Math.max(2, item.kwh / maximum * 100)) + '%' }} /></div>
            <span>{months[item.month - 1]}</span>
          </div>
        ))}
      </div>
      <details className="monthly-details">
        <summary>View exact monthly values</summary>
        <div className="monthly-grid">
          {data.monthlyKwh.map(item => <div key={item.month}><span>{months[item.month - 1]}</span><strong>{kwh(item.kwh)}</strong></div>)}
        </div>
      </details>
      <p className="source-note">Estimated with PVGIS 5.3, 14% system loss and an optimal panel orientation. Actual roof conditions and weather will change results.</p>
    </section>
  )
}

function BatteryCard({ siteId }: { siteId: number }) {
  const [capacity, setCapacity] = useState('10')
  const [annualUse, setAnnualUse] = useState('3500')
  const [result, setResult] = useState<Battery | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => { setResult(null); setError('') }, [siteId])

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setResult(null)
    try {
      const params = new URLSearchParams({ capacityKwh: capacity, annualUseKwh: annualUse })
      setResult(await api<Battery>('/api/sites/' + siteId + '/battery?' + params.toString()))
    } catch (reason) {
      setError(errorText(reason))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel battery-panel">
      <div className="panel-header">
        <div><div className="eyebrow">BATTERY SCENARIO</div><h2>See what storage adds</h2></div>
        <span className="battery-symbol" aria-hidden="true">▱</span>
      </div>
      <p className="panel-intro">Compare how much solar energy the household can use directly, and how much more it can use with a home battery.</p>
      <form className="scenario-form" onSubmit={submit}>
        <label><span>Battery capacity</span><div className="input-unit"><input type="number" min="0" max="1000" step="any" value={capacity} onChange={event => setCapacity(event.target.value)} required /><em>kWh</em></div></label>
        <label><span>Annual electricity use</span><div className="input-unit"><input type="number" min="0.01" max="1000000" step="any" value={annualUse} onChange={event => setAnnualUse(event.target.value)} required /><em>kWh</em></div></label>
        <button className="button primary" disabled={busy} type="submit">{busy ? 'Calculating…' : 'Compare scenarios'} <span aria-hidden="true">↗</span></button>
      </form>
      {error && <div className="alert error" role="alert">{error}</div>}
      {result && (
        <div className="scenario-results" aria-live="polite">
          <div className="gain-banner"><span>ADDITIONAL SOLAR USED WITH BATTERY</span><strong>+{kwh(result.batteryGainKwh)}</strong></div>
          <div className="comparison-grid">
            <div className="comparison-card"><div className="comparison-label">WITHOUT BATTERY</div><strong>{kwh(result.withoutBattery.selfUsedKwh)}</strong><span>solar used at home</span><div className="comparison-rule" /><dl><dt>Solar exported</dt><dd>{kwh(result.withoutBattery.exportedKwh)}</dd><dt>Grid supplied</dt><dd>{kwh(result.withoutBattery.gridImportedKwh)}</dd><dt>Self-sufficiency</dt><dd>{decimal.format(result.withoutBattery.selfSufficiencyPercent)}%</dd></dl></div>
            <div className="comparison-card emphasized"><div className="comparison-label">WITH BATTERY</div><strong>{kwh(result.withBattery.selfUsedKwh)}</strong><span>solar used at home</span><div className="comparison-rule" /><dl><dt>Solar exported</dt><dd>{kwh(result.withBattery.exportedKwh)}</dd><dt>Grid supplied</dt><dd>{kwh(result.withBattery.gridImportedKwh)}</dd><dt>Self-sufficiency</dt><dd>{decimal.format(result.withBattery.selfSufficiencyPercent)}%</dd></dl></div>
          </div>
          <p className="source-note">Illustrative model: household use is spread evenly across the year; the battery starts empty, charges only from solar, and uses 95% efficiency in each direction. Hourly PVGIS 2023 output is aligned to the monthly estimate. No tariffs or bill savings are implied.</p>
        </div>
      )}
    </section>
  )
}

export default function App() {
  const [initializing, setInitializing] = useState(true)
  const [userEmail, setUserEmail] = useState<string | null>(null)
  const [sites, setSites] = useState<Site[]>([])
  const [sitesLoading, setSitesLoading] = useState(false)
  const [sitesError, setSitesError] = useState('')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [editing, setEditing] = useState<Site | 'new' | null>(null)
  const [production, setProduction] = useState<Production | null>(null)
  const [productionError, setProductionError] = useState('')
  const [productionLoading, setProductionLoading] = useState(false)
  const [productionVersion, setProductionVersion] = useState(0)

  useEffect(() => {
    api<{ email: string }>('/api/me')
      .then(result => setUserEmail(result.email))
      .catch(() => setUserEmail(null))
      .finally(() => setInitializing(false))
  }, [])

  useEffect(() => {
    if (!userEmail) return
    setSitesLoading(true)
    setSitesError('')
    api<Site[]>('/api/sites')
      .then(setSites)
      .catch(reason => setSitesError(errorText(reason)))
      .finally(() => setSitesLoading(false))
  }, [userEmail])

  useEffect(() => {
    if (selectedId === null) return
    let active = true
    setProduction(null)
    setProductionError('')
    setProductionLoading(true)
    api<Production>('/api/sites/' + selectedId + '/production')
      .then(result => { if (active) setProduction(result) })
      .catch(reason => { if (active) setProductionError(errorText(reason)) })
      .finally(() => { if (active) setProductionLoading(false) })
    return () => { active = false }
  }, [selectedId, productionVersion])

  async function saveSite(input: SiteInput) {
    if (editing === 'new') {
      const created = await api<Site>('/api/sites', { method: 'POST', body: JSON.stringify(input) })
      setSites(current => [created, ...current])
      setEditing(null)
      setSelectedId(created.id)
    } else if (editing) {
      const updated = await api<Site>('/api/sites/' + editing.id, { method: 'PUT', body: JSON.stringify(input) })
      setSites(current => current.map(site => site.id === updated.id ? updated : site))
      setEditing(null)
      setProductionVersion(value => value + 1)
    }
  }

  async function removeSite(site: Site) {
    if (!window.confirm('Delete ' + site.clientName + ' and its site details? This cannot be undone.')) return
    try {
      await api<void>('/api/sites/' + site.id, { method: 'DELETE' })
      setSites(current => current.filter(item => item.id !== site.id))
      setSelectedId(null)
    } catch (reason) {
      window.alert(errorText(reason))
    }
  }

  async function logout() {
    try {
      await api<void>('/api/logout', { method: 'POST' })
      setUserEmail(null)
      setSites([])
      setSelectedId(null)
    } catch (reason) {
      window.alert(errorText(reason))
    }
  }

  if (initializing) return <div className="startup"><Brand /><div className="spinner" /><span>Preparing your workspace…</span></div>
  if (!userEmail) return <AuthScreen onAuthenticated={setUserEmail} />

  const selected = sites.find(site => site.id === selectedId) ?? null
  const title = selected ? selected.clientName : 'Your client sites'

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Brand />
        <div className="sidebar-section-label">WORKSPACE</div>
        <button className={'nav-item ' + (!selected && !editing ? 'active' : '')} onClick={() => { setEditing(null); setSelectedId(null) }}><span aria-hidden="true">▦</span> Overview</button>
        <button className="nav-item" onClick={() => { setSelectedId(null); setEditing('new') }}><span aria-hidden="true">＋</span> Add site</button>
        <div className="sidebar-bottom">
          <div className="advisor-avatar">{userEmail[0].toUpperCase()}</div>
          <div className="advisor-identity"><strong>Advisor account</strong><span title={userEmail}>{userEmail}</span></div>
          <button className="logout-button" onClick={logout} title="Sign out" aria-label="Sign out">↗</button>
        </div>
      </aside>
      <div className="main-column">
        <header className="topbar">
          <div className="breadcrumb"><span>Workspace</span><span className="crumb-separator">/</span><strong>{editing ? editing === 'new' ? 'New site' : 'Edit site' : title}</strong></div>
          <div className="topbar-right"><span className="status-dot" /> Advisor workspace</div>
        </header>
        {editing ? (
          <SiteForm key={editing === 'new' ? 'new' : editing.id} site={editing === 'new' ? null : editing} onSave={saveSite} onCancel={() => setEditing(null)} />
        ) : selected ? (
          <main className="content-page">
            <button className="back-link" onClick={() => setSelectedId(null)}>← All client sites</button>
            <div className="page-heading detail-heading">
              <div><div className="eyebrow">SITE OVERVIEW</div><h1>{selected.clientName}</h1><p>{selected.address}</p></div>
              <div className="heading-actions"><button className="button subtle" onClick={() => setEditing(selected)}>Edit site</button><button className="button danger-quiet" onClick={() => removeSite(selected)}>Delete</button></div>
            </div>
            <div className="site-meta">
              <div><span>PANEL CAPACITY</span><strong>{decimal.format(selected.peakKwp)} kWp</strong></div>
              <div><span>COORDINATES</span><strong>{decimal.format(selected.latitude)}°, {decimal.format(selected.longitude)}°</strong></div>
              <div><span>ROOF AREA</span><strong>{selected.roofAreaM2 == null ? 'Not provided' : decimal.format(selected.roofAreaM2) + ' m²'}</strong></div>
            </div>
            <ProductionCard data={production} error={productionError} loading={productionLoading} retry={() => setProductionVersion(value => value + 1)} />
            <BatteryCard key={String(selected.id) + '-' + String(productionVersion)} siteId={selected.id} />
          </main>
        ) : (
          <main className="content-page">
            <div className="page-heading">
              <div><div className="eyebrow">OVERVIEW</div><h1>Your client sites</h1><p>Manage locations and explore the potential of solar, one site at a time.</p></div>
              <button className="button primary" onClick={() => setEditing('new')}>Add new site <span aria-hidden="true">↗</span></button>
            </div>
            <div className="overview-metrics"><div><span>ACTIVE SITES</span><strong>{sites.length}</strong></div><div><span>TOTAL PANEL CAPACITY</span><strong>{decimal.format(sites.reduce((total, site) => total + site.peakKwp, 0))} <small>kWp</small></strong></div><div className="metric-decoration" aria-hidden="true">◐</div></div>
            <div className="section-title"><div><div className="eyebrow">PORTFOLIO</div><h2>Sites</h2></div><span>{sites.length} {sites.length === 1 ? 'site' : 'sites'}</span></div>
            {sitesLoading ? <div className="panel loading-panel"><div className="spinner" />Loading your sites…</div> : sitesError ? <div className="alert error" role="alert">{sitesError}</div> : sites.length === 0 ? (
              <div className="empty-state"><div className="empty-icon" aria-hidden="true">✳</div><h3>Your workspace starts here</h3><p>Add your first client site to explore its solar production and a battery scenario.</p><button className="button primary" onClick={() => setEditing('new')}>Add first site <span aria-hidden="true">↗</span></button></div>
            ) : (
              <div className="site-grid">
                {sites.map(site => <button className="site-card" key={site.id} onClick={() => setSelectedId(site.id)}><div className="site-card-top"><span className="site-icon" aria-hidden="true">✳</span><span className="site-arrow" aria-hidden="true">↗</span></div><h3>{site.clientName}</h3><p>{site.address}</p><div className="site-card-bottom"><span>{decimal.format(site.peakKwp)} kWp capacity</span><span>View analysis</span></div></button>)}
              </div>
            )}
          </main>
        )}
        <footer className="app-footer"><span>Solar Sites</span><span>Estimates powered by PVGIS · European Commission</span></footer>
      </div>
    </div>
  )
}
