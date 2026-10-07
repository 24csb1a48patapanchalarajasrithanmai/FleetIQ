const STATUS_LABEL = {
  reposition_in: 'Send vehicles in',
  reposition_out: 'Pull vehicles out',
  balanced: 'Balanced',
}

export default function FleetAllocationPanel({ allocations, totalVehicles }) {
  return (
    <div className="panel alloc-panel">
      <div className="panel-title-row">
        <h2>Fleet allocation recommendations</h2>
        <span className="panel-subtitle mono">{totalVehicles} VEHICLES TOTAL</span>
      </div>
      <div className="alloc-table">
        <div className="alloc-header mono">
          <span>Zone</span>
          <span>Demand share</span>
          <span>Vehicles</span>
          <span>Action</span>
        </div>
        <div className="alloc-body">
          {allocations.map(a => (
            <div className="alloc-row" key={a.zone_id}>
              <div className="alloc-zone">
                <span className="alloc-zone-name">{a.zone_name}</span>
                <span className="alloc-zone-borough mono">{a.borough}</span>
              </div>
              <span className="mono">{a.demand_share_pct}%</span>
              <span className="mono alloc-vehicles">{a.recommended_vehicles}</span>
              <span className={`badge ${a.status}`}>{STATUS_LABEL[a.status]}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
