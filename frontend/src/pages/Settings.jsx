import { useEffect, useState } from 'react'
import KillSwitch from '../components/KillSwitch'
import { apiFetch } from '../services/api'

export default function Settings() {
  const [rules, setRules] = useState({ risk_per_trade_usd: 50, max_daily_loss_usd: 1000, max_open_positions: 10, max_spread_points: 50, min_risk_reward: 2, stop_loss_pips: 50, max_take_profit_pips: 100, pip_size: 0.01 })
  const [status, setStatus] = useState(null)
  const [message, setMessage] = useState('')
  async function loadSettings() {
    const [statusResponse, rulesResponse] = await Promise.all([
      apiFetch('/api/control/status'),
      apiFetch('/api/control/risk-rules'),
    ])
    if (!statusResponse.ok || !rulesResponse.ok) throw new Error('Unable to load settings')
    setStatus(await statusResponse.json())
    setRules(await rulesResponse.json())
  }
  useEffect(() => {
    let active = true
    const refresh = () => loadSettings().catch(() => { if (active) setStatus(null) })
    refresh()
    const timer = window.setInterval(refresh, 3000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [])
  async function save(event) {
    event.preventDefault()
    const response = await apiFetch('/api/control/risk-rules', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(rules) })
    const data = await response.json()
    setMessage(response.ok ? 'Risk rules saved.' : data.detail || 'Unable to save rules.')
  }
  async function toggle() {
    const response = await apiFetch('/api/control/toggle', { method: 'POST' })
    setStatus(await response.json())
  }
  return <section className="page"><p className="eyebrow">SAFETY / CONTROL</p><h1>Settings</h1>
    <div className="dashboard-panel"><h2>Trading control <span className={`execution-badge ${status?.execution_enabled ? 'live' : 'dry'}`}>{status?.execution_enabled ? 'DEMO LIVE' : 'DRY-RUN'}</span></h2><p>Status: {status?.running ? 'running' : 'stopped'} · Kill switch: {status?.kill_switch ? 'active' : 'off'} · Approved signals execute automatically.</p><div className="control-actions"><KillSwitch /><button className={`toggle-button ${status?.running ? 'on' : 'off'}`} onClick={toggle} type="button"><span /> System {status?.running ? 'ON' : 'OFF'}</button></div></div>
    <form className="dashboard-panel settings-form" onSubmit={save}><h2>Risk rules</h2><p className="live-note">EMA entries use a {rules.stop_loss_pips || 0}-pip stop and a {rules.max_take_profit_pips || 0}-pip target (1:{rules.min_risk_reward || 0}). Each position risks ${rules.risk_per_trade_usd || 0}; up to {rules.max_open_positions || 0} positions may be open.</p>{Object.keys(rules).map((key) => <label key={key}>{key.replaceAll('_', ' ')}<input type="number" step="any" min="0" value={rules[key]} onChange={(event) => setRules({ ...rules, [key]: Number(event.target.value) })} /></label>)}<button type="submit">Save risk rules</button>{message && <p>{message}</p>}</form>
  </section>
}