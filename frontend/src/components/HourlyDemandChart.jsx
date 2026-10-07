import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="chart-tooltip mono">
      <div>{String(label).padStart(2, '0')}:00</div>
      <div className="chart-tooltip-value">{payload[0].value} rides</div>
    </div>
  )
}

export default function HourlyDemandChart({ data, peakHour, scopeLabel }) {
  return (
    <div className="panel chart-panel">
      <div className="panel-title-row">
        <h2>Predicted demand by hour</h2>
        <span className="panel-subtitle mono">{scopeLabel}</span>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <AreaChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: -16 }}>
          <defs>
            <linearGradient id="demandFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3FE0CB" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#3FE0CB" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#1A222B" vertical={false} />
          <XAxis
            dataKey="hour"
            tickFormatter={h => String(h).padStart(2, '0')}
            stroke="#6C7A88"
            fontSize={11}
            tickLine={false}
          />
          <YAxis stroke="#6C7A88" fontSize={11} tickLine={false} width={40} />
          <Tooltip content={<CustomTooltip />} />
          {peakHour !== undefined && (
            <ReferenceLine x={peakHour} stroke="#F5A93F" strokeDasharray="4 4" label={{ value: 'peak', fill: '#F5A93F', fontSize: 11, position: 'top' }} />
          )}
          <Area type="monotone" dataKey="predicted_demand" stroke="#3FE0CB" strokeWidth={2} fill="url(#demandFill)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
