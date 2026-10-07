export default function TopZonesPanel({ zones, onSelect }) {
  const max = Math.max(1, ...zones.map(z => z.predicted_demand))

  return (
    <div className="panel ranking-panel">
      <div className="panel-title-row">
        <h2>Top-demand zones</h2>
        <span className="panel-subtitle mono">RIDES / HR</span>
      </div>
      <ol className="ranking-list">
        {zones.map((z, i) => (
          <li key={z.zone_id} className="ranking-row" onClick={() => onSelect?.(z.zone_id)}>
            <span className="ranking-index mono">{String(i + 1).padStart(2, '0')}</span>
            <div className="ranking-body">
              <div className="ranking-label-row">
                <span className="ranking-name">{z.zone_name}</span>
                <span className={`badge ${z.demand_level}`}>{z.demand_level.replace('_', ' ')}</span>
              </div>
              <div className="ranking-bar-track">
                <div
                  className="ranking-bar-fill"
                  style={{ width: `${(z.predicted_demand / max) * 100}%` }}
                />
              </div>
            </div>
            <span className="ranking-value mono">{z.predicted_demand}</span>
          </li>
        ))}
      </ol>
    </div>
  )
}
