export default function Header({ modelInfo, health }) {
  return (
    <header className="app-header">
      <div className="brand">
        <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true">
          <rect width="32" height="32" rx="7" fill="#11161C" />
          <circle cx="16" cy="16" r="10" fill="none" stroke="#3FE0CB" strokeWidth="1.6" />
          <circle cx="16" cy="16" r="2.4" fill="#F5A93F" />
          <path d="M16 6 L16 16 L23 12" stroke="#3FE0CB" strokeWidth="1.6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <div>
          <h1>FleetIQ</h1>
          <p>Demand prediction &amp; fleet allocation console</p>
        </div>
      </div>

      <div className="header-status">
        {health && (
          <span className="status-pill">
            <span className="dot" style={{ background: 'var(--accent-cyan)' }} />
            API online
          </span>
        )}
        {modelInfo && (
          <span className="status-pill mono">
            {modelInfo.best_model?.toUpperCase()} · R² {modelInfo.metrics?.[modelInfo.best_model]?.r2?.toFixed(3)}
          </span>
        )}
        {modelInfo && (
          <span className="status-pill mono">
            MAE {modelInfo.metrics?.[modelInfo.best_model]?.mae?.toFixed(2)} rides
          </span>
        )}
      </div>
    </header>
  )
}
