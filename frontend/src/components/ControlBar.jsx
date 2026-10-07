export default function ControlBar({
  zones, zoneId, setZoneId,
  timestamp, setTimestamp,
  totalVehicles, setTotalVehicles,
}) {
  const grouped = zones.reduce((acc, z) => {
    (acc[z.Borough] ||= []).push(z)
    return acc
  }, {})

  return (
    <section className="control-bar panel">
      <div className="control-field">
        <label htmlFor="zone-select">Zone</label>
        <select id="zone-select" value={zoneId} onChange={e => setZoneId(Number(e.target.value))}>
          {Object.entries(grouped).map(([borough, zs]) => (
            <optgroup key={borough} label={borough}>
              {zs.map(z => (
                <option key={z.zone_id} value={z.zone_id}>{z.Zone}</option>
              ))}
            </optgroup>
          ))}
        </select>
      </div>

      <div className="control-field">
        <label htmlFor="ts-input">Forecast time</label>
        <input
          id="ts-input"
          type="datetime-local"
          value={timestamp}
          onChange={e => setTimestamp(e.target.value)}
        />
      </div>

      <div className="control-field">
        <label htmlFor="fleet-input">Fleet size</label>
        <input
          id="fleet-input"
          type="number"
          min={1}
          max={5000}
          value={totalVehicles}
          onChange={e => setTotalVehicles(Number(e.target.value))}
        />
      </div>

      <p className="control-hint">
        Model trained on Jan–Apr 2024 synthetic trip data. Times within that window use real recent-demand history;
        times outside it fall back to each zone's average pattern.
      </p>
    </section>
  )
}
