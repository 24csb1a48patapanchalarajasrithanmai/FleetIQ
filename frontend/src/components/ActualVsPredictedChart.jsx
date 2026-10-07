import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

function fmtTime(ts) {
  const d = new Date(ts)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}h`
}

export default function ActualVsPredictedChart({ series }) {
  const data = series.map(s => ({ ...s, label: fmtTime(s.timestamp) }))

  return (
    <div className="panel chart-panel">
      <div className="panel-title-row">
        <h2>Actual vs. predicted — city-wide, held-out test period</h2>
        <span className="panel-subtitle mono">LAST {data.length}H</span>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: -16 }}>
          <CartesianGrid stroke="#1A222B" vertical={false} />
          <XAxis dataKey="label" stroke="#6C7A88" fontSize={10} tickLine={false} interval={Math.ceil(data.length / 8)} />
          <YAxis stroke="#6C7A88" fontSize={11} tickLine={false} width={44} />
          <Tooltip
            contentStyle={{ background: '#161D25', border: '1px solid #232C36', borderRadius: 8, fontFamily: 'IBM Plex Mono, monospace', fontSize: 12 }}
            labelStyle={{ color: '#AAB6C2' }}
          />
          <Legend wrapperStyle={{ fontSize: 12, fontFamily: 'Inter, sans-serif' }} />
          <Line type="monotone" dataKey="actual" name="Actual" stroke="#6E93F7" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="predicted" name="Predicted" stroke="#3FE0CB" strokeWidth={2} dot={false} strokeDasharray="5 3" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
