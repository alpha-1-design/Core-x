# Global Command Center 2050 - Specification

## Project Overview

**Project Name:** Global Command Center 2050  
**Type:** Real-time monitoring dashboard  
**Core Functionality:** Connect to any virtual system anywhere in the world, visualize on a 3D globe, drill down into locations with real-time data  
**Target Users:** System administrators, operators monitoring global infrastructure

---

## UI/UX Specification

### Layout Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│ HEADER: Logo, Title, Global Status Indicator                        │
├────────────┬──────────────────────────────────┬────────────────────┤
│            │                                  │                    │
│ LEFT PANEL │       MAIN - 3D GLOBE            │   RIGHT PANEL      │
│ Connection │                                  │   Detail View      │
│ List       │                                  │   Live Data        │
│            │                                  │   Terminal         │
│            │                                  │                    │
├────────────┴──────────────────────────────────┴────────────────────┤
│ FOOTER: Health Bars, Latency, System Time                          │
└─────────────────────────────────────────────────────────────────────┘
```

**Responsive Breakpoints:**
- Desktop: Full 3-column layout (≥1200px)
- Tablet: 2-column, right panel collapsible (768px-1199px)
- Mobile: Single column with tabs (≤767px)

### Visual Design

**Theme:** Dark holographic command center

**Color Palette:**
- Background: `#0a0a12` (deep space black)
- Panel BG: `#12121f` (dark navy)
- Primary: `#00ff9d` (cyber green)
- Secondary: `#00b8ff` (electric blue)
- Warning: `#ffaa00` (amber)
- Danger: `#ff3366` (neon red)
- Text Primary: `#e0e0e8`
- Text Muted: `#6a6a7a`
- Grid Lines: `#1a1a2e`
- Glow: `rgba(0, 255, 157, 0.3)`

**Typography:**
- Headings: `Orbitron`, monospace fallback
- Body: `JetBrains Mono`, monospace
- Data/Numbers: `Share Tech Mono`
- Base size: 14px

**Effects:**
- Scanline overlay (subtle)
- Glow effects on active elements
- Pulse animations for alerts
- Grid pattern on panels

### Components

1. **Connection Card** (left panel)
   - Status indicator dot (green/orange/red)
   - Name, location, type
   - Mini sparkline chart
   - States: normal, warning, offline

2. **3D Globe** (main area)
   - Earth with wireframe grid
   - Connection markers (glowing spheres)
   - Connection lines to origin
   - Drag rotation, zoom, click selection

3. **Detail Panel** (right)
   - Selected connection info
   - Real-time metrics graph
   - Command terminal input

4. **Footer**
   - System health bars
   - Average latency
   - UTC time display

5. **Add Connection Modal**
   - Form: Name, Type, URL/Endpoint, Location (lat/lng), Credentials

---

## Functionality Specification

### Core Features

1. **Universal Connector System**
   - Add any endpoint: API, Database, Server, Sensor, Stream
   - Configure connection details (URL, auth, polling interval)
   - Test connectivity

2. **3D Globe Visualization**
   - Render Earth with continent hints
   - Plot connections as interactive markers
   - Drag to rotate, scroll to zoom
   - Click marker to select and show details

3. **Real-time Data Updates**
   - Poll connections at configured intervals
   - Update metrics live on globe and panels
   - Simulated data for demo endpoints

4. **Alerts System**
   - Auto-detect offline/warning connections
   - Visual pulse on globe markers
   - Alert list in right panel

5. **Command Terminal**
   - Send commands to connections
   - View response in terminal output

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/connections` | List all connections |
| POST | `/api/connections` | Add new connection |
| PUT | `/api/connections/:id` | Update connection |
| DELETE | `/api/connections/:id` | Remove connection |
| POST | `/api/connections/:id/ping` | Test connectivity |
| POST | `/api/connections/:id/command` | Send command |
| GET | `/api/metrics` | Get all current metrics |
| GET | `/api/alerts` | Get active alerts |

### Demo Connections (Pre-seeded)

8 locations worldwide:
1. US West - San Francisco (API Server)
2. US East - New York (Data Center)
3. Europe - London (Cloud Node)
4. Europe - Frankfurt (Sensor Array)
5. Asia - Tokyo (Satellite Link)
6. Asia - Singapore (Maritime Sensor)
7. Australia - Sydney (Weather Station)
8. Africa - Cape Town (Research Station)

---

## Acceptance Criteria

- [ ] Flask server starts without errors
- [ ] 3D globe renders with Earth and starfield
- [ ] All 8 demo connections appear as markers on globe
- [ ] Markers are color-coded by status
- [ ] Drag rotation works on globe
- [ ] Click marker shows detail panel
- [ ] Connection list populates in left panel
- [ ] Real-time updates occur (simulated)
- [ ] Add connection modal works
- [ ] Footer shows health stats

---

## Tech Stack

- **Backend:** Python Flask, Flask-CORS
- **Frontend:** Vanilla JS, Three.js (CDN)
- **Fonts:** Google Fonts (Orbitron, JetBrains Mono, Share Tech Mono)
- **Deployment:** Render (free tier)