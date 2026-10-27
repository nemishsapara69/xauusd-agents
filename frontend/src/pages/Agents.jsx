import { useEffect, useState } from 'react'

function readablePayload(agent, payload) {
  if (!payload) return 'Waiting for data'
  if (agent === 'analysis') {
    return `Trend ${payload.trend || 'no trade'} · M15 ${payload.m15 || '—'} · H1 ${payload.h1 || '—'} · ${payload.alignment || 'timeframes not aligned'}`
  }
  if (agent === 'level') {
    return payload.side
      ? `${payload.side.toUpperCase()} signal · entry ${payload.entry} · stop ${payload.sl} · target ${payload.tp}`
      : 'No confirmed EMA retest'
  }
  if (agent === 'news') return payload.trade_allowed === false ? `Trading blocked · ${payload.reason || 'high-impact event window'}` : 'No blocking high-impact event'
  if (agent === 'risk') return payload.approved ? `Approved · risk $${payload.risk_amount} · volume ${payload.lot_size}` : `Rejected · ${String(payload.reason || 'risk rule').replaceAll('_', ' ')}`
  return payload.status ? String(payload.status).replaceAll('_', ' ') : 'Updated'
}

const agentDefinitions = [
  { key: 'news', name: 'News Filter', icon: '01', description: 'Screens high-impact events' },
  { key: 'analysis', name: 'Analysis Agent', icon: '02', description: 'Aligns M15 and H1 EMA trend' },
  { key: 'level', name: 'Level Agent', icon: '03', description: 'Finds M15 EMA retests' },
  { key: 'risk', name: 'Risk Agent', icon: '04', description: 'Checks exposure and reward' },
  { key: 'reporting', name: 'Execution', icon: '05', description: 'Routes approved orders' },
]

function activityState(agent, payload) {
  if (!payload) return 'waiting'
  if (agent === 'news' && payload.trade_allowed === false) return 'blocked'
  if (agent === 'risk' && payload.approved === false) return 'blocked'
  if (agent === 'reporting' && payload.status === 'not_executed') return 'standby'
  if (agent === 'risk' && payload.approved) return 'approved'
  return 'active'
}

function decisionRows(agent, payload) {
  if (!payload) return []
  if (agent === 'news') return [
    ['Market gate', payload.trade_allowed === false ? 'BLOCKED' : 'CLEAR'],
    ['Reason', payload.reason || 'No blocking event'],
  ]
  if (agent === 'analysis') return [
    ['Trend', payload.trend || 'waiting'],
    ['M15 / H1', `${payload.m15 || '—'} / ${payload.h1 || '—'}`],
    ['Alignment', payload.alignment || 'Not aligned'],
  ]
  if (agent === 'level') return payload.side ? [
    ['Direction', payload.side.toUpperCase()],
    ['Entry', payload.entry],
    ['Stop / target', `${payload.sl} / ${payload.tp}`],
    ['Reward / risk', payload.risk_reward ? `1:${Number(payload.risk_reward).toFixed(2)}` : '—'],
  ] : [['Setup', 'No confirmed EMA retest']]
  if (agent === 'risk') return [
    ['Decision', payload.approved ? 'APPROVED' : 'REJECTED'],
    ['Risk budget', payload.risk_amount != null ? `$${payload.risk_amount}` : '—'],
    ['Position size', payload.lot_size != null ? `${payload.lot_size} lot` : '—'],
    ['Rule result', String(payload.reason || '—').replaceAll('_', ' ')],
  ]
  return [
    ['Route', String(payload.status || 'waiting').replaceAll('_', ' ')],
    ['Action', payload.message || 'Awaiting next instruction'],
  ]
}

export default function Agents({ lastEvent }) {
  const [selectedAgent, setSelectedAgent] = useState('analysis')
  const [steps, setSteps] = useState([])
  useEffect(() => {
    if (lastEvent?.type === 'agent_step') {
      setSteps((current) => [...current, lastEvent].slice(-30))
    }
    if (lastEvent?.type === 'agent_update') {
      setSteps((current) => [...current, {
        type: 'agent_step',
        agent: 'analysis',
        timestamp: lastEvent.timestamp,
        payload: lastEvent.payload.result,
      }, {
        type: 'agent_step',
        agent: 'level',
        timestamp: lastEvent.timestamp,
        payload: lastEvent.payload.signal || { status: 'no_signal' },
      }].slice(-30))
    }
  }, [lastEvent])
  const result = lastEvent?.type === 'agent_update' ? lastEvent.payload : null
  const trend = result?.result?.trend || 'waiting'
  const selectedSteps = steps.filter((step) => step.agent === selectedAgent)
  const latestByAgent = agentDefinitions.reduce((result, agent) => {
    result[agent.key] = steps.filter((step) => step.agent === agent.key).at(-1)
    return result
  }, {})
  const selectedDefinition = agentDefinitions.find((agent) => agent.key === selectedAgent)
  const selectedRows = decisionRows(selectedAgent, latestByAgent[selectedAgent]?.payload)
  const cycleEvents = steps.slice(-5)
  return (
    <section className="page">
      <p className="eyebrow">AGENT NETWORK / LIVE</p>
      <h1>Agent operations room</h1>
      <div className="operations-strip">
        <span className="operations-live"><i /> LIVE PIPELINE</span>
        <span>News → Analysis → Levels → Risk → Execution</span>
        <span className="operations-time">{lastEvent?.timestamp ? new Date(lastEvent.timestamp).toLocaleTimeString() : 'Awaiting feed'}</span>
      </div>
      <div className="office-floor">
        <div className="office-grid-lines" />
        {agentDefinitions.filter((agent) => agent.key !== 'risk' && agent.key !== 'reporting').map((agent) => {
          const step = latestByAgent[agent.key]
          const payload = step?.payload
          const state = activityState(agent.key, payload)
          const status = agent.key === 'analysis' ? payload?.trend || trend : state
          return (
            <article className={`agent-card operations-card office-agent office-${agent.key} ${selectedAgent === agent.key ? 'selected' : ''}`} key={agent.key} onClick={() => setSelectedAgent(agent.key)}>
              <div className="operations-card-top"><span className="agent-number">{agent.icon}</span><span className={`agent-pulse ${state}`} /><span className={`agent-state ${state}`}>{status}</span></div>
              <h2>{agent.name}</h2>
              <p className="operations-description">{agent.description}</p>
              <div className="operations-message">{readablePayload(agent.key, payload)}</div>
              <div className="operations-footer"><span>{step?.timestamp ? new Date(step.timestamp).toLocaleTimeString() : 'No update yet'}</span><span className="activity-bars"><i /><i /><i /></span></div>
            </article>
          )
        })}
        <div className="office-connector connector-a" />
        <div className="office-connector connector-b" />
        <div className="office-connector connector-c" />
        <div className="office-connector connector-d" />
        <section className="command-desk">
          <div className="desk-header"><div><p className="eyebrow">COMMAND DESK / LIVE</p><h2>Risk &amp; Execution workspace</h2></div><span className="desk-status"><i /> SUPERVISED</span></div>
          {['risk', 'reporting'].map((key) => {
            const agent = agentDefinitions.find((item) => item.key === key)
            const step = latestByAgent[key]
            const payload = step?.payload
            const state = activityState(key, payload)
            return <button className={`desk-module ${selectedAgent === key ? 'selected' : ''}`} key={key} onClick={() => setSelectedAgent(key)} type="button"><div className="desk-module-top"><span className={`desk-module-icon ${state}`}>{key === 'risk' ? 'R' : 'E'}</span><span><b>{agent.name}</b><small>{agent.description}</small></span><em className={state}>{key === 'risk' ? (payload?.approved ? 'PASS' : payload ? 'CHECK' : 'WAIT') : String(payload?.status || 'WAIT').replaceAll('_', ' ')}</em></div><div className="desk-module-copy">{readablePayload(key, payload)}</div><div className="desk-meter"><i className={state} /></div></button>
          })}
          <div className="desk-footer"><span>Risk budget <b>$50 / position</b></span><span>Target <b>1:2</b></span><span>Approval <b>Manual</b></span></div>
        </section>
      </div>
      <div className="decision-console">
        <div className="decision-console-heading">
          <div><p className="eyebrow">DECISION CONSOLE</p><h2>How the pipeline is working</h2></div>
          <span className="console-caption">CLICK A MODULE TO INSPECT</span>
        </div>
        <div className="pipeline-track">
          {agentDefinitions.map((agent, index) => {
            const step = latestByAgent[agent.key]
            const state = activityState(agent.key, step?.payload)
            return <button className={`pipeline-node ${selectedAgent === agent.key ? 'active' : ''}`} key={agent.key} onClick={() => setSelectedAgent(agent.key)} type="button"><span className={`pipeline-node-dot ${state}`} /><b>{agent.name.replace(' Agent', '')}</b>{index < agentDefinitions.length - 1 && <i />}</button>
          })}
        </div>
        <div className="decision-detail">
          <div className="decision-detail-title"><span className={`detail-pulse ${activityState(selectedAgent, latestByAgent[selectedAgent]?.payload)}`} /><div><b>{selectedDefinition?.name}</b><small>{selectedDefinition?.description}</small></div><span className="detail-time">{latestByAgent[selectedAgent]?.timestamp ? new Date(latestByAgent[selectedAgent].timestamp).toLocaleTimeString() : 'waiting'}</span></div>
          <div className="decision-rows">{selectedRows.length ? selectedRows.map(([label, value]) => <div key={label}><span>{label}</span><b>{value}</b></div>) : <div className="decision-empty">Waiting for the first live event from this module.</div>}</div>
        </div>
      </div>
      <div className="pipeline-line"><span /> Pipeline updates are streamed from the live orchestration cycle <span /></div>
      <div className="dashboard-panel agent-stream">
        <div className="stream-heading"><div><p className="eyebrow">SELECTED MODULE</p><h2>{agentDefinitions.find((agent) => agent.key === selectedAgent)?.name} live reasoning</h2></div><span className="stream-live-dot">● STREAMING</span></div>
        <p>Every update below comes from the live orchestration cycle, not simulated movement.</p>
        {selectedSteps.length ? selectedSteps.slice().reverse().map((step, index) => (
          <div className="agent-log-row" key={`${step.timestamp || index}-${index}`}><time>{step.timestamp ? new Date(step.timestamp).toLocaleTimeString() : 'live'}</time><span>{readablePayload(selectedAgent, step.payload)}</span></div>
        )) : <p className="empty">Waiting for the next M15 orchestration cycle.</p>}
      </div>
      <div className="cycle-ticker"><span className="ticker-label">LATEST CYCLE</span>{cycleEvents.length ? cycleEvents.map((step, index) => <span className="ticker-event" key={`${step.timestamp}-${step.agent}-${index}`}><i />{step.agent}</span>) : <span className="ticker-empty">No live cycle received yet</span>}</div>
    </section>
  )
}
