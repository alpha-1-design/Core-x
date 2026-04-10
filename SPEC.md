# Global Situational Awareness Dashboard - SPEC

## Project Overview

**Project Name:** Global Watch  
**Type:** Real-time global monitoring dashboard  
**Core Functionality:** Monitor worldwide events (news, disasters, conflicts, tech) visualized on an interactive 3D globe with real-time updates  
**Target Users:** Analysts, operators, decision-makers monitoring global situations

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    3D GLOBE                         │
│   Real Earth texture with hotspot overlays           │
└─────────────────────────────────────────────────────┘
         ▲                    ▲                    ▲
┌────────┴────────┐  ┌───────┴───────┐  ┌────────┴────────┐
│  News Monitor   │  │  Quake Monitor │  │  Weather/Alert │
│  (NewsAPI)      │  │  (USGS API)    │  │  (OpenWeather) │
└─────────────────┘  └───────────────┘  └────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │  WebSocket Server │
                    │  (real-time push) │
                    └───────────────────┘
```

---

## Data Sources

| Source | API | Category | Update Frequency |
|--------|-----|----------|------------------|
| News | NewsAPI.org | Politics, Tech, World | 15 min |
| Earthquakes | USGS | Disasters | 5 min |
| Weather | OpenWeatherMap | Alerts | 30 min |
| Conflict | ACLED | Geopolitical | Daily |

---

## UI/UX Specification

### Layout Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│ HEADER: Logo, Title, Category Filters, Live Indicator              │
├────────────────────────────┬────────────────────────────────────────┤
│                            │                                        │
│      CATEGORY PANEL        │           3D GLOBE                     │
│   - News (by region)       │    Real Earth texture                  │
│   - Earthquakes             │    Hotspot overlays                    │
│   - Weather alerts          │    Clickable markers                   │
│   - Conflicts               │                                        │
│                            │                                        │
├────────────────────────────┴────────────────────────────────────────┤
│ DETAIL PANEL: Selected location events, timeline, sources           │
├─────────────────────────────────────────────────────────────────────┤
│ FOOTER: Last update, Active events count, System status            │
└─────────────────────────────────────────────────────────────────────┘
```

### Visual Design

**Theme:** Dark command center with vibrant status colors

**Color Palette:**
- Background: `#0a0e17` (deep space navy)
- Panel BG: `#111827` (dark slate)
- Normal: `#10b981` (emerald green)
- Caution: `#f59e0b` (amber)
- Critical: `#ef4444` (red)
- Info: `#3b82f6` (blue)
- Text Primary: `#f1f5f9`
- Text Muted: `#64748b`

**Typography:**
- Headings: `Space Grotesk`, sans-serif
- Body: `Inter`, sans-serif
- Data: `JetBrains Mono`

---

## Functionality Specification

### Core Features

1. **Real Earth Globe**
   - High-res Earth texture
   - Smooth drag rotation, zoom
   - Country/region highlighting based on events

2. **Hotspot Detection**
   - Score events by region (0-100)
   - Color overlay: green (0-25), yellow (26-50), orange (51-75), red (76-100)
   - Animated pulse on critical hotspots

3. **Event Categories**
   - News (geo-tagged articles)
   - Earthquakes (magnitude + depth)
   - Weather alerts (storms, floods)
   - Conflict incidents

4. **Real-time Updates**
   - WebSocket for instant push
   - Polling fallback every 60s
   - Visual indicator for new events

5. **Location Details**
   - Click/tap globe marker
   - Side panel shows events for that region
   - Event cards with source, time, summary

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/events` | All active events |
| GET | `/api/events?category=news` | Filter by category |
| GET | `/api/events?lat=X&lng=Y&radius=500` | Events near location |
| GET | `/api/regions` | All regions with scores |
| GET | `/api/regions/:code` | Single region details |
| WS | `/ws` | WebSocket for live updates |

---

## Tech Stack

- **Backend:** Python Flask, Flask-SocketIO
- **Frontend:** Vanilla JS, Three.js
- **Real-time:** Flask-SocketIO (WebSocket)
- **Earth Texture:** NASA Blue Marble (or similar)
- **Deployment:** Render

---

## Acceptance Criteria

- [ ] Real Earth texture renders on globe
- [ ] USGS earthquake data displays as markers
- [ ] News articles map to countries
- [ ] Hotspots color-code regions by activity level
- [ ] Click marker shows event details
- [ ] WebSocket pushes new events in real-time
- [ ] Category filters work
- [ ] Footer shows live update timestamp
