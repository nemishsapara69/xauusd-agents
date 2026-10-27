import { useEffect, useState } from 'react'
import Navbar from './components/Navbar'
import { useWebSocket } from './hooks/useWebSocket'
import LiveChart from './pages/LiveChart'
import Agents from './pages/Agents'
import Dashboard from './pages/Dashboard'
import Trades from './pages/Trades'
import Reports from './pages/Reports'
import Logs from './pages/Logs'
import Login from './pages/Login'
import Settings from './pages/Settings'
import './App.css'

const pageNames = {
  '/': 'Dashboard',
  '/chart': 'Live Chart',
  '/agents': 'Agents',
  '/trades': 'Trades',
  '/settings': 'Settings',
  '/reports': 'Reports',
  '/logs': 'Logs',
}

function Placeholder({ title }) {
  return (
    <section className="page placeholder">
      <p className="eyebrow">XAUUSD CONTROL CENTER</p>
      <h1>{title}</h1>
      <p>This page is reserved for the next trading-system phase.</p>
    </section>
  )
}

function currentPath() {
  return window.location.hash.replace(/^#/, '') || '/'
}

function App() {
  const [authenticated, setAuthenticated] = useState(Boolean(sessionStorage.getItem('xauusd_token')))
  const [path, setPath] = useState(currentPath)
  const { status, lastEvent } = useWebSocket(authenticated)
  useEffect(() => {
    const onHashChange = () => setPath(currentPath())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  useEffect(() => {
    const expire = () => setAuthenticated(false)
    window.addEventListener('auth-expired', expire)
    return () => window.removeEventListener('auth-expired', expire)
  }, [])

  if (!authenticated) return <Login onLogin={() => setAuthenticated(true)} />

  const content =
    path === '/' ? <Dashboard lastEvent={lastEvent} /> :
    path === '/chart' ? (
      <LiveChart lastEvent={lastEvent} />
    ) : path === '/agents' ? (
      <Agents lastEvent={lastEvent} />
    ) : path === '/trades' ? <Trades lastEvent={lastEvent} /> :
    path === '/reports' ? <Reports lastEvent={lastEvent} /> :
    path === '/logs' ? <Logs lastEvent={lastEvent} /> :
    path === '/settings' ? <Settings /> : (
      <Placeholder title={pageNames[path] || 'Page not found'} />
    )

  return (
    <div className="app-shell">
      <Navbar wsStatus={status} />
      <main>{content}</main>
      <footer>Demo-live execution · Automatic trade execution · <button onClick={() => { sessionStorage.removeItem('xauusd_token'); setAuthenticated(false) }} type="button">Sign out</button></footer>
    </div>
  )
}

export default App
