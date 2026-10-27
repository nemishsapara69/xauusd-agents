const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export function getToken() {
  return sessionStorage.getItem('xauusd_token')
}

export async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers || {})
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers })
  if (response.status === 401) {
    sessionStorage.removeItem('xauusd_token')
    window.dispatchEvent(new Event('auth-expired'))
  }
  return response
}

export async function fetchCandles(timeframe = 'M15', count = 500) {
  const response = await apiFetch(`/api/candles?tf=${encodeURIComponent(timeframe)}&count=${count}`)
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `Candle request failed (${response.status})`)
  }
  return response.json()
}

export function websocketUrl() {
  const url = new URL(API_BASE_URL)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.pathname = '/ws'
  const token = getToken()
  if (token) url.searchParams.set('token', token)
  return url.toString()
}

export async function fetchChartTrades() {
  const response = await apiFetch('/api/chart-trades')
  if (!response.ok) throw new Error('Trade history request failed')
  return response.json()
}

export { API_BASE_URL }