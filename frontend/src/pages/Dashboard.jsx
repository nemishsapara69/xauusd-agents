import { useEffect, useRef, useState } from 'react'
import { apiFetch } from '../services/api'

export default function Dashboard({ lastEvent }) {
  const [data, setData] = useState(null)
  const previousEquity = useRef(null)
  const [equityDirection, setEquityDirection] = useState('flat')
  const [agentActivity, setAgentActivity] = useState(null)
  useEffect(() => {
    let active = true
    const refresh = () => apiFetch('/api/dashboard').then((response) => response.json()).then((nextData) => {
      if (!active) return
      const currentEquity = Number(nextData.equity)
      if (Number.isFinite(currentEquity) && previousEquity.current != null) {
        setEquityDirection(currentEquity > previousEquity.current ? 'up' : currentEquity < previousEquity.current ? 'down' : 'flat')
      }
      if (Number.isFinite(currentEquity)) previousEquity.current = currentEquity
      setData(nextData)
    }).catch(() => { if (active) setData(null) })
    refresh()
    const timer = window.setInterval(refresh, 3000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [])
  useEffect(() => {
    if (lastEvent?.type === 'agent_update') setAgentActivity(lastEvent)
    if (lastEvent?.type === 'account_update') {
      const currentEquity = Number(lastEvent.payload?.equity)
      if (Number.isFinite(currentEquity) && previousEquity.current != null) {
        setEquityDirection(currentEquity > previousEquity.current ? 'up' : currentEquity < previousEquity.current ? 'down' : 'flat')
      }
      if (Number.isFinite(currentEquity)) previousEquity.current = currentEquity
      setData((current) => ({ ...current, ...lastEvent.payload, account_status: 'connected' }))
      return
    }
  }, [lastEvent])
  const stats = data || {}
  const currency = stats.account_currency || 'USD'
  const formatMoney = (value) => value == null
    ? '—'
    : `${currency} ${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  return <section className="page"><p className="eyebrow">OVERVIEW / XAUUSD</p><h1>Trading dashboard</h1>
    <div className="stat-grid">
      <div className="stat-card"><span>Demo balance</span><strong>{formatMoney(stats.balance)}</strong></div>
      <div className={`stat-card live-money ${equityDirection}`}><span>Live equity</span><strong>{formatMoney(stats.equity)} <small>{equityDirection === 'up' ? '▲' : equityDirection === 'down' ? '▼' : '•'}</small></strong></div>
      <div className="stat-card"><span>Today&apos;s P&amp;L</span><strong>${Number(stats.today_pnl || 0).toFixed(2)}</strong></div>
      <div className="stat-card"><span>Trades</span><strong>{stats.trades || 0}</strong></div>
      <div className="stat-card"><span>Win rate</span><strong>{Number(stats.win_rate || 0).toFixed(1)}%</strong></div>
      <div className="stat-card"><span>Open trades</span><strong>{stats.open_trades || 0}</strong></div>
    </div>
    <div className="dashboard-panel"><h2>System status <span className={`connection-status ${stats.account_status || 'unavailable'}`}>{stats.account_status === 'connected' ? 'MT5 connected' : 'MT5 unavailable'}</span></h2><p>{stats.account_server ? `Account ${stats.account_server} is supplying live balance and equity. ` : 'MT5 account data is currently unavailable. '}{stats.execution_enabled ? 'Demo-live execution is enabled.' : 'Dry-run execution is active.'}</p></div>
    <div className="dashboard-panel live-analysis"><h2>Live analysis feed <span>updates every second</span></h2><p>{agentActivity ? `Trend: ${agentActivity.payload?.result?.trend || 'no_trade'} · M15: ${agentActivity.payload?.result?.m15 || '—'} · H1: ${agentActivity.payload?.result?.h1 || '—'} · ${agentActivity.payload?.signal ? `Signal: ${agentActivity.payload.signal.side}` : 'No entry signal'}` : 'Waiting for live market analysis.'}</p></div>
  </section>
}