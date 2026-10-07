function intensityColor(t) {
  // t in [0,1] -> deep panel blue through cyan to amber to rose
  if (t < 0.35) return `rgba(63, 224, 203, ${0.15 + t})`
  if (t < 0.7) return `rgba(245, 169, 63, ${0.35 + (t - 0.35)})`
  return `rgba(240, 87, 122, ${0.5 + (t - 0.7)})`
}

export default function ZonePulseStrip({ data, zoneName }) {
  const max = Math.max(1, ...data.map(d => d.predicted_demand))
  const currentHour = new Date().getHours()

  return (
    <div className="panel pulse-panel">
      <div className="panel-title-row">
        <h2>24h demand pulse</h2>
        <span className="panel-subtitle mono">{zoneName || 'CITYWIDE'}</span>
      </div>
      <div className="pulse-strip">
        {data.map(d => {
          const t = d.predicted_demand / max
          return (
            <div className="pulse-cell" key={d.hour}>
              <div
                className="pulse-bar"
                style={{
                  height: `${12 + t * 68}%`,
                  background: intensityColor(t),
                  boxShadow: d.hour === currentHour ? '0 0 0 1px var(--accent-cyan)' : 'none',
                }}
                title={`${String(d.hour).padStart(2, '0')}:00 — ${d.predicted_demand} rides`}
              />
              <span className="pulse-hour mono">{d.hour % 3 === 0 ? String(d.hour).padStart(2, '0') : ''}</span>
            </div>
          )
        })}
      </div>
      <div className="pulse-legend mono">
        <span><i className="dot" style={{ background: '#3FE0CB' }} /> low</span>
        <span><i className="dot" style={{ background: '#F5A93F' }} /> high</span>
        <span><i className="dot" style={{ background: '#F0577A' }} /> very high</span>
      </div>
    </div>
  )
}
