const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:5000' : '';
let socket = null;
let eventListeners = {};

async function fetcher(url, options = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);
  
  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
      mode: 'cors'
    });
    clearTimeout(timeoutId);
    return res;
  } catch (e) {
    clearTimeout(timeoutId);
    throw e;
  }
}

const api = {
  async getEvents(params = {}) {
    try {
      let url = `${API_BASE}/api/events`;
      const queryParams = [];
      if (params.category) queryParams.push(`category=${params.category}`);
      if (params.lat !== undefined) queryParams.push(`lat=${params.lat}`);
      if (params.lng !== undefined) queryParams.push(`lng=${params.lng}`);
      if (params.radius) queryParams.push(`radius=${params.radius}`);
      if (queryParams.length) url += '?' + queryParams.join('&');
      
      const res = await fetcher(url);
      return await res.json();
    } catch (e) {
      console.error('Failed to fetch events:', e);
      return [];
    }
  },

  async getRegions() {
    try {
      const res = await fetcher(`${API_BASE}/api/regions`);
      return await res.json();
    } catch (e) {
      console.error('Failed to fetch regions:', e);
      return [];
    }
  },

  async getStats() {
    try {
      const res = await fetcher(`${API_BASE}/api/stats`);
      return await res.json();
    } catch (e) {
      console.error('Failed to fetch stats:', e);
      return null;
    }
  },

  async summarize(eventId) {
    try {
      const res = await fetcher(`${API_BASE}/api/summarize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_id: eventId })
      });
      return await res.json();
    } catch (e) {
      return null;
    }
  },

  async analyzeSentiment(eventId) {
    try {
      const res = await fetcher(`${API_BASE}/api/sentiment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_id: eventId })
      });
      return await res.json();
    } catch (e) {
      return null;
    }
  },

  async getWeather(lat, lng) {
    try {
      const res = await fetcher(`${API_BASE}/api/weather/${lat}/${lng}`);
      return await res.json();
    } catch (e) {
      return null;
    }
  }
};

function initSocketIO() {
  if (typeof io === 'undefined') {
    console.warn('Socket.IO not loaded');
    return;
  }
  
  socket = io(API_BASE, {
    transports: ['websocket', 'polling'],
    reconnection: true
  });
  
  socket.on('connect', () => {
    console.log('WebSocket connected');
    document.getElementById('liveIndicator')?.classList.add('active');
  });
  
  socket.on('disconnect', () => {
    document.getElementById('liveIndicator')?.classList.remove('active');
  });
  
  socket.on('update', (data) => {
    if (eventListeners['update']) {
      eventListeners['update'].forEach(cb => cb(data));
    }
  });
}

const socketIO = {
  on(event, callback) {
    if (!eventListeners[event]) eventListeners[event] = [];
    eventListeners[event].push(callback);
  },
  emit(event, data) {
    if (socket) socket.emit(event, data);
  }
};

window.api = api;
window.socketIO = socketIO;

document.addEventListener('DOMContentLoaded', initSocketIO);
