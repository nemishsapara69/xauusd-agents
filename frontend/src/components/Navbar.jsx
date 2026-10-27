const links = [
  ['/', 'Dashboard'],
  ['/chart', 'Live Chart'],
  ['/agents', 'Agents'],
  ['/trades', 'Trades'],
  ['/settings', 'Settings'],
  ['/reports', 'Reports'],
  ['/logs', 'Logs'],
]

export default function Navbar({ wsStatus }) {
  return (
    <header className="navbar">
      <a className="brand" href="#/">
        <span className="brand-mark">Au</span>
        <span>XAUUSD Control</span>
      </a>
      <nav aria-label="Primary navigation">
        {links.map(([href, label]) => (
          <a key={href} href={`#${href}`}>
            {label}
          </a>
        ))}
      </nav>
      <span className={`ws-status ${wsStatus}`}>
        <span className="status-dot" />
        WS {wsStatus}
      </span>
    </header>
  )
}