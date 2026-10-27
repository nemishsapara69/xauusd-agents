import { useEffect, useState } from 'react'
import { apiFetch } from '../services/api'
export default function Logs({ lastEvent }) {
  const [events, setEvents] = useState([])
  useEffect(() => { apiFetch('/api/logs').then((response) => response.json()).then((data) => setEvents(data.events || [])).catch(() => setEvents([])) }, [lastEvent])
  return <section className="page"><p className="eyebrow">AUDIT TRAIL</p><h1>Logs</h1><div className="log-list">{events.map((event) => <div className="log-row" key={event.id}><strong>{event.agent}</strong><span>{event.event_type}</span><small>{event.created_at}</small></div>)}</div></section>
}