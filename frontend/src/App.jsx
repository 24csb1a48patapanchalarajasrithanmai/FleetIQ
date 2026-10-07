import { useEffect, useMemo, useState } from 'react'
import api from './api'
import './App.css'

import Header from './components/Header'
import ControlBar from './components/ControlBar'
import KpiCards from './components/KpiCards'
import HourlyDemandChart from './components/HourlyDemandChart'
import ZonePulseStrip from './components/ZonePulseStrip'
import TopZonesPanel from './components/TopZonesPanel'
import ActualVsPredictedChart from './components/ActualVsPredictedChart'
import FleetAllocationPanel from './components/FleetAllocationPanel'

const DEFAULT_TIMESTAMP = '2024-04-25T18:00'

export default function App() {
  const [health, setHealth] = useState(null)
  const [modelInfo, setModelInfo] = useState(null)
  const [zones, setZones] = useState([])

  const [zoneId, setZoneId] = useState(null)
  const [timestamp, setTimestamp] = useState(DEFAULT_TIMESTAMP)
  const [totalVehicles, setTotalVehicles] = useState(200)

  const [zonePrediction, setZonePrediction] = useState(null)
  const [hourlyPattern, setHourlyPattern] = useState(null)
  const [topZones, setTopZones] = useState([])
  const [avp, setAvp] = useState([])
  const [allocations, setAllocations] = useState([])

  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([api.health(), api.modelInfo(), api.zones(), api.actualVsPredicted(120)])
      .then(([h, m, z, series]) => {
        setHealth(h)
        setModelInfo(m)
        setZones(z.zones)
        setZoneId(z.zones[0]?.zone_id ?? null)
        setAvp(series.series)
      })
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (zoneId == null) return
    const isoTs = timestamp ? new Date(timestamp).toISOString() : undefined

    Promise.all([
      api.predict(zoneId, isoTs),
      api.hourlyPattern(zoneId),
      api.topZones(isoTs, 8),
      api.fleetAllocation(isoTs, totalVehicles),
    ])
      .then(([pred, pattern, top, alloc]) => {
        setZonePrediction(pred)
        setHourlyPattern(pattern)
        setTopZones(top.top_zones)
        setAllocations(alloc.allocations)
      })
      .catch(e => setError(String(e)))
  }, [zoneId, timestamp, totalVehicles])

  const zoneAllocation = useMemo(
    () => allocations.find(a => a.zone_id === zoneId),
    [allocations, zoneId]
  )

  const topZone = topZones[0]

  if (loading) {
    return (
      <div className="app-loading">
        <div className="spinner" />
        <p>Connecting to FleetIQ API…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="app-loading">
        <p className="error-text">Couldn't reach the FleetIQ API.</p>
        <p className="error-detail mono">{error}</p>
        <p className="error-hint">
          Make sure the backend is running: <code>uvicorn app.main:app --reload</code> from the{' '}
          <code>backend/</code> directory, on port 8000 (or set <code>VITE_API_BASE_URL</code>).
        </p>
      </div>
    )
  }

  return (
    <div className="app-shell">
      <Header modelInfo={modelInfo} health={health} />

      <ControlBar
        zones={zones}
        zoneId={zoneId}
        setZoneId={setZoneId}
        timestamp={timestamp}
        setTimestamp={setTimestamp}
        totalVehicles={totalVehicles}
        setTotalVehicles={setTotalVehicles}
      />

      <KpiCards
        zonePrediction={zonePrediction}
        hourlyPattern={hourlyPattern}
        topZone={topZone}
        zoneAllocation={zoneAllocation}
      />

      <section className="grid-2">
        {hourlyPattern && (
          <HourlyDemandChart
            data={hourlyPattern.hourly_pattern}
            peakHour={hourlyPattern.peak_hour}
            scopeLabel={zonePrediction?.zone_name?.toUpperCase() || 'CITYWIDE'}
          />
        )}
        {hourlyPattern && (
          <ZonePulseStrip data={hourlyPattern.hourly_pattern} zoneName={zonePrediction?.zone_name} />
        )}
      </section>

      <section className="grid-2">
        <TopZonesPanel zones={topZones} onSelect={setZoneId} />
        {avp.length > 0 && <ActualVsPredictedChart series={avp} />}
      </section>

      <section>
        {allocations.length > 0 && (
          <FleetAllocationPanel allocations={allocations} totalVehicles={totalVehicles} />
        )}
      </section>

      <footer className="app-footer">
        FleetIQ · NYC TLC-style demand forecasting · model trained through {modelInfo?.trained_through}
      </footer>
    </div>
  )
}
