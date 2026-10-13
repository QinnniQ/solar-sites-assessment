export type Site = {
  id: number
  clientName: string
  address: string
  latitude: number
  longitude: number
  roofAreaM2: number | null
  peakKwp: number
}

export type SiteInput = Omit<Site, 'id'>
export type Production = {
  yearlyKwh: number
  monthlyKwh: { month: number; kwh: number }[]
}
export type EnergyCase = {
  selfUsedKwh: number
  exportedKwh: number
  gridImportedKwh: number
  selfConsumptionPercent: number
  selfSufficiencyPercent: number
  endingChargeKwh?: number
}
export type Battery = {
  productionKwh: number
  consumptionKwh: number
  withoutBattery: EnergyCase
  withBattery: EnergyCase
  batteryGainKwh: number
}

export class ApiError extends Error {
  status: number
  fields: Record<string, string>

  constructor(status: number, message: string, fields: Record<string, string> = {}) {
    super(message)
    this.status = status
    this.fields = fields
  }
}

function csrfToken(): string {
  const cookie = document.cookie.split('; ').find(part => part.startsWith('solar_csrf='))
  return cookie ? decodeURIComponent(cookie.split('=').slice(1).join('=')) : ''
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = options.method?.toUpperCase() ?? 'GET'
  const headers = new Headers(options.headers)
  if (options.body) headers.set('Content-Type', 'application/json')
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method) && path !== '/api/register' && path !== '/api/login') {
    headers.set('X-CSRF-Token', csrfToken())
  }
  let response: Response
  try {
    response = await fetch(path, { ...options, headers, credentials: 'same-origin' })
  } catch {
    throw new ApiError(0, 'The application could not reach its server. Check your connection and try again.')
  }
  if (response.status === 204) return undefined as T
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    const fields = payload?.errors ?? {}
    const message =
      payload?.error?.message ??
      payload?.detail ??
      (Object.keys(fields).length ? 'Please correct the highlighted fields.' : 'Something went wrong. Please try again.')
    throw new ApiError(response.status, message, fields)
  }
  return payload as T
}
