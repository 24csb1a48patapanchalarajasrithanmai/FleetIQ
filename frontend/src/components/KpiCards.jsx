function Card({ label, value, sub, badge }) {
  return (
    <div className="kpi-card panel">
      <span className="kpi-label">{label}</span>
      <div className="kpi-value-row">
        <span className="kpi-value mono">{value}</span>
        {badge && <span className={`badge ${badge.level}`}>{badge.text}</span>}
      </div>
      {sub && <span className="kpi-sub">{sub}</span>}
    </div>
  )
}

export default function KpiCards({ zonePrediction, hourlyPattern, topZone, zoneAllocation }) {
  return (
    <section className="kpi-grid">
      <Card
        label="Predicted demand — selected zone"
        value={zonePrediction ? `${zonePrediction.predicted_demand} rides/hr` : '—'}
        sub={zonePrediction?.zone_name}
        badge={zonePrediction && { level: zonePrediction.demand_level, text: zonePrediction.demand_level.replace('_', ' ') }}
      />
      <Card
        label="Peak demand hour (24h)"
        value={hourlyPattern ? `${String(hourlyPattern.peak_hour).padStart(2, '0')}:00` : '—'}
        sub="Highest predicted hour for this scope"
      />
      <Card
        label="Highest-demand zone right now"
        value={topZone ? `${topZone.predicted_demand} rides/hr` : '—'}
        sub={topZone?.zone_name}
        badge={topZone && { level: topZone.demand_level, text: topZone.demand_level.replace('_', ' ') }}
      />
      <Card
        label="Vehicles recommended — selected zone"
        value={zoneAllocation ? `${zoneAllocation.recommended_vehicles} vehicles` : '—'}
        sub={zoneAllocation && `${zoneAllocation.demand_share_pct}% of city demand`}
        badge={zoneAllocation && { level: zoneAllocation.status, text: zoneAllocation.status.replace('_', ' ') }}
      />
    </section>
  )
}
