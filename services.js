const API_BASE = '';
let socket = null;
let eventListeners = {};

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
      
      const res = await fetch(url);
      return await res.json();
    } catch (e) {
      console.error('Failed to fetch events:', e);
      return [];
    }
  },

  async getRegions() {
    try {
      const res = await fetch(`${API_BASE}/api/regions`);
      return await res.json();
    } catch (e) {
      console.error('Failed to fetch regions:', e);
      return [];
    }
  },

  async getRegion(code) {
    try {
      const res = await fetch(`${API_BASE}/api/regions/${code}`);
      return await res.json();
    } catch (e) {
      console.error('Failed to fetch region:', e);
      return null;
    }
  },

  async getStats() {
    try {
      const res = await fetch(`${API_BASE}/api/stats`);
      return await res.json();
    } catch (e) {
      console.error('Failed to fetch stats:', e);
      return null;
    }
  }
};

function initSocketIO() {
  if (typeof io === 'undefined') {
    console.warn('Socket.IO not loaded');
    return;
  }
  
  socket = io(API_BASE || window.location.origin, {
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 10
  });
  
  socket.on('connect', () => {
    console.log('WebSocket connected');
    document.getElementById('liveIndicator')?.classList.add('active');
  });
  
  socket.on('disconnect', () => {
    console.log('WebSocket disconnected');
    document.getElementById('liveIndicator')?.classList.remove('active');
  });
  
  socket.on('update', (data) => {
    if (eventListeners['update']) {
      eventListeners['update'].forEach(cb => cb(data));
    }
  });
  
  socket.on('new_event', (event) => {
    if (eventListeners['new_event']) {
      eventListeners['new_event'].forEach(cb => cb(event));
    }
  });
}

const socketIO = {
  on(event, callback) {
    if (!eventListeners[event]) {
      eventListeners[event] = [];
    }
    eventListeners[event].push(callback);
  },
  
  off(event, callback) {
    if (eventListeners[event]) {
      eventListeners[event] = eventListeners[event].filter(cb => cb !== callback);
    }
  },
  
  emit(event, data) {
    if (socket) {
      socket.emit(event, data);
    }
  }
};

window.api = api;
window.socketIO = socketIO;

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    const script = document.createElement('script');
    script.src = 'https://cdn.socket.io/4.7.5/socket.io.min.js';
    document.head.appendChild(script);
    script.onload = initSocketIO;
  });
} else {
  const script = document.createElement('script');
  script.src = 'https://cdn.socket.io/4.7.5/socket.io.min.js';
  document.head.appendChild(script);
  script.onload = initSocketIO;
}
