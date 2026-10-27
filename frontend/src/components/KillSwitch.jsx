import { useState } from 'react'
import { apiFetch } from '../services/api'

export default function KillSwitch() {
  const [blocked, setBlocked] = useState(false)
  const [message, setMessage] = useState('')
  async function activate() {
    const response = await apiFetch('/api/control/kill-switch?close_all=false', { method: 'POST' })
    const data = await response.json()
    if (response.ok) {
      setBlocked(true)
      setMessage(data.kill_switch ? 'New trades blocked.' : 'Control updated.')
    } else setMessage(data.detail || 'Unable to activate kill switch')
  }
  return <div className="kill-switch"><button className="danger-button" disabled={blocked} onClick={activate} type="button">{blocked ? 'Kill switch active' : 'Activate kill switch'}</button>{message && <small>{message}</small>}</div>
}