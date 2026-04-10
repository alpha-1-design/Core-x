const API_BASE = '';

const api = {
  async getConnections() {
    try {
      const res = await fetch(`${API_BASE}/api/connections`);
      return await res.json();
    } catch (e) {
      console.warn('API unavailable, using fallback data');
      return getFallbackConnections();
    }
  },

  async addConnection(data) {
    const res = await fetch(`${API_BASE}/api/connections`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await res.json();
  },

  async updateConnection(id, data) {
    const res = await fetch(`${API_BASE}/api/connections/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await res.json();
  },

  async deleteConnection(id) {
    const res = await fetch(`${API_BASE}/api/connections/${id}`, { method: 'DELETE' });
    return await res.json();
  },

  async pingConnection(id) {
    const res = await fetch(`${API_BASE}/api/connections/${id}/ping`, { method: 'POST' });
    return await res.json();
  },

  async sendCommand(id, command) {
    const res = await fetch(`${API_BASE}/api/connections/${id}/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command })
    });
    return await res.json();
  },

  async getMetrics() {
    try {
      const res = await fetch(`${API_BASE}/api/metrics`);
      return await res.json();
    } catch (e) {
      return {};
    }
  },

  async getAlerts() {
    try {
      const res = await fetch(`${API_BASE}/api/alerts`);
      return await res.json();
    } catch (e) {
      return [];
    }
  },

  async getConnectionData(id) {
    try {
      const res = await fetch(`${API_BASE}/api/data/${id}`);
      return await res.json();
    } catch (e) {
      return [];
    }
  }
};

function getFallbackConnections() {
  return [
    { id: 'us-west', name: 'SF Gateway', type: 'API Server', lat: 37.7749, lng: -122.4194, status: 'online', metrics: { cpu: 45, memory: 62, latency: 34, throughput: 850 } },
    { id: 'us-east', name: 'NYC Data Center', type: 'Data Center', lat: 40.7128, lng: -74.0060, status: 'online', metrics: { cpu: 78, memory: 55, latency: 28, throughput: 1200 } },
    { id: 'eu-london', name: 'London Cloud', type: 'Cloud Node', lat: 51.5074, lng: -0.1278, status: 'warning', metrics: { cpu: 89, memory: 81, latency: 145, throughput: 420 } },
    { id: 'eu-frankfurt', name: 'Sensor Array Alpha', type: 'Sensor Array', lat: 50.1109, lng: 8.6821, status: 'online', metrics: { cpu: 23, memory: 41, latency: 52, throughput: 180 } },
    { id: 'asia-tokyo', name: 'Tokyo Satellite', type: 'Satellite Link', lat: 35.6762, lng: 139.6503, status: 'online', metrics: { cpu: 56, memory: 48, latency: 89, throughput: 620 } },
    { id: 'asia-singapore', name: 'Maritime Sensor', type: 'Maritime Sensor', lat: 1.3521, lng: 103.8198, status: 'offline', metrics: { cpu: 0, memory: 0, latency: 0, throughput: 0 } },
    { id: 'aus-sydney', name: 'Weather Station NSW', type: 'Weather Station', lat: -33.8688, lng: 151.2093, status: 'online', metrics: { cpu: 12, memory: 28, latency: 156, throughput: 95 } },
    { id: 'africa-cape', name: 'Research Hub', type: 'Research Station', lat: -33.9249, lng: 18.4241, status: 'online', metrics: { cpu: 34, memory: 45, latency: 178, throughput: 210 } }
  ];
}