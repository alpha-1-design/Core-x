# Global Watch

Real-time world monitoring at your fingertips.

Global Watch puts the world's events in front of you as they happen. Natural disasters, breaking news, tech developments, and global events are visible on a live 3D globe with real-time updates. It's situational awareness for everyone, not just analysts.

---

## Features

**Live 3D Globe**

- Interactive Earth visualization
- Drag to rotate, scroll to zoom, double-click to zoom
- Keyboard controls: arrows to rotate, +/- to zoom, Home to reset
- Pinch-to-zoom on touch devices
- Hover tooltips on markers
- Fly-to animations on event selection
- Minimap for orientation
- Atmosphere with real-time sun position
- Hotspots light up by region activity level

**Multiple Data Sources**

- Earthquakes from USGS (4.5+ magnitude)
- World news from Reddit r/worldnews
- Tech stories from Hacker News
- Global events from GDELT

**Real-time Updates**

- WebSocket push for live data
- Auto-refresh every 60 seconds
- Visual alerts for critical events

**Filter by Category**

- All, News, Tech, Earthquakes, or Conflicts
- Click any filter to isolate that data

**Severity Indicators**

- Critical (red), High (orange), Medium (yellow), Low (blue)

**Regional Scores**

- Countries highlighted by activity level
- Click regions to see local events

---

## Use Cases

**For Individuals**

- Stay informed about what's happening globally
- Track events in your region
- Understand world patterns

**For Journalists**

- Identify breaking stories early
- See regional activity spikes
- Source verification context

**For Researchers**

- Historical event tracking
- Correlation patterns
- Data for analysis

**For Educators**

- Global awareness teaching tool
- Current events discussions
- Geography and news cross-learning

---

## Future Vision

Global Watch is exploring a collaboration with MiroFish, a multi-agent AI simulation engine.

**The Possibility**

Real events come in through Global Watch. MiroFish simulates thousands of AI agents reacting to those events. The system predicts how events might unfold.

**Why This Matters**

- Disaster response: Predict impact zones before they happen
- Policy foresight: See public reaction before passing laws
- Early warning: Detect escalation before it spirals
- Journalism: Know which stories will break tomorrow

We're not there yet. But combining real-time awareness with predictive simulation could transform how we understand and anticipate the world.

---

## Tech Stack

- Frontend: Vanilla JavaScript, Three.js
- Backend: Python Flask, Flask-SocketIO
- Deployment: Render

---

## Deployment

**Local**

    pip install -r requirements.txt
    python server.py
    
Visit http://localhost:5000

**Production**

Deploy to Render. The app auto-configures from render.yaml.

    gh repo clone alpha-1-design/Core-x

Set environment variables as needed.

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| /api/events | All active events |
| /api/events?category=news | Filter by category |
| /api/events?lat=X&lng=Y&radius=500 | Events near location |
| /api/regions | All regions with scores |
| /api/stats | Summary statistics |
| /api/refresh | Force data refresh |
| /ws | WebSocket for live updates |

---

## Contributing

Open source. Contributions welcome.

1. Fork the repo
2. Make changes
3. Submit a PR

---

## License

MIT