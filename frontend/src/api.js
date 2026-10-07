import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const client = axios.create({ baseURL: BASE_URL, timeout: 15000 })

export const api = {
  health: () => client.get('/api/health').then(r => r.data),
  zones: () => client.get('/api/zones').then(r => r.data),
  predict: (zoneId, timestamp) =>
    client.get('/api/predict', { params: { zone_id: zoneId, timestamp } }).then(r => r.data),
  topZones: (timestamp, limit = 10) =>
    client.get('/api/demand/top-zones', { params: { timestamp, limit } }).then(r => r.data),
  hourlyPattern: (zoneId) =>
    client.get('/api/demand/hourly-pattern', { params: zoneId ? { zone_id: zoneId } : {} }).then(r => r.data),
  actualVsPredicted: (limit = 168) =>
    client.get('/api/demand/actual-vs-predicted', { params: { limit } }).then(r => r.data),
  fleetAllocation: (timestamp, totalVehicles = 200) =>
    client.get('/api/fleet/allocation', { params: { timestamp, total_vehicles: totalVehicles } }).then(r => r.data),
  modelInfo: () => client.get('/api/model/info').then(r => r.data),
}

export default api
