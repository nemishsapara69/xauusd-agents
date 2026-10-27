import { useState } from 'react'
import { API_BASE_URL } from '../services/api'

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const submit = async (event) => {
    event.preventDefault()
    setError('')
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      setError(data.detail || 'Login failed')
      return
    }
    sessionStorage.setItem('xauusd_token', data.access_token)
    onLogin()
  }
  return <main className="login-shell"><form className="login-card" onSubmit={submit}>
    <p className="eyebrow">XAUUSD CONTROL</p><h1>Sign in</h1>
    <label>Username<input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required /></label>
    <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required /></label>
    {error && <p className="alert">{error}</p>}<button type="submit">Sign in</button>
  </form></main>
}
