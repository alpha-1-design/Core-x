import os
import time
import json
import requests
import threading
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

HTML_CONTENT = None
JS_CONTENT = None
SERVICES_CONTENT = None

NEWS_API_KEY = os.environ.get('NEWS_API_KEY', '')
USGS_API = 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson'

COUNTRY_COORDS = {
    'US': {'lat': 37.09, 'lng': -95.71, 'name': 'United States'},
    'CN': {'lat': 35.86, 'lng': 104.19, 'name': 'China'},
    'RU': {'lat': 61.52, 'lng': 105.31, 'name': 'Russia'},
    'IN': {'lat': 20.59, 'lng': 78.96, 'name': 'India'},
    'BR': {'lat': -14.23, 'lng': -51.92, 'name': 'Brazil'},
    'GB': {'lat': 55.37, 'lng': -3.43, 'name': 'United Kingdom'},
    'FR': {'lat': 46.22, 'lng': 2.21, 'name': 'France'},
    'DE': {'lat': 51.16, 'lng': 10.45, 'name': 'Germany'},
    'JP': {'lat': 36.20, 'lng': 138.25, 'name': 'Japan'},
    'IL': {'lat': 31.04, 'lng': 34.85, 'name': 'Israel'},
    'UA': {'lat': 48.37, 'lng': 31.16, 'name': 'Ukraine'},
    'IR': {'lat': 32.42, 'lng': 53.68, 'name': 'Iran'},
    'KP': {'lat': 40.33, 'lng': 127.51, 'name': 'North Korea'},
    'PK': {'lat': 30.37, 'lng': 69.34, 'name': 'Pakistan'},
    'TR': {'lat': 38.96, 'lng': 35.24, 'name': 'Turkey'},
    'SA': {'lat': 23.88, 'lng': 45.07, 'name': 'Saudi Arabia'},
    'ZA': {'lat': -30.55, 'lng': 22.93, 'name': 'South Africa'},
    'AU': {'lat': -25.27, 'lng': 133.77, 'name': 'Australia'},
    'CA': {'lat': 56.13, 'lng': -106.34, 'name': 'Canada'},
    'MX': {'lat': 23.63, 'lng': -102.55, 'name': 'Mexico'},
    'EG': {'lat': 26.82, 'lng': 30.80, 'name': 'Egypt'},
    'KR': {'lat': 35.90, 'lng': 127.76, 'name': 'South Korea'},
    'AF': {'lat': 33.93, 'lng': 67.70, 'name': 'Afghanistan'},
    'SY': {'lat': 34.80, 'lng': 38.99, 'name': 'Syria'},
    'IQ': {'lat': 33.22, 'lng': 43.67, 'name': 'Iraq'},
    'LY': {'lat': 26.33, 'lng': 17.22, 'name': 'Libya'},
    'YE': {'lat': 15.55, 'lng': 48.51, 'name': 'Yemen'},
    'SD': {'lat': 12.86, 'lng': 30.21, 'name': 'Sudan'},
    'ET': {'lat': 9.14, 'lng': 40.48, 'name': 'Ethiopia'},
    'NG': {'lat': 9.08, 'lng': 8.67, 'name': 'Nigeria'},
    'CO': {'lat': 4.57, 'lng': -74.29, 'name': 'Colombia'},
    'VE': {'lat': 6.42, 'lng': -66.58, 'name': 'Venezuela'},
    'AR': {'lat': -38.41, 'lng': -63.61, 'name': 'Argentina'},
    'ID': {'lat': -0.78, 'lng': 113.92, 'name': 'Indonesia'},
    'TH': {'lat': 15.87, 'lng': 100.99, 'name': 'Thailand'},
    'MM': {'lat': 21.91, 'lng': 95.95, 'name': 'Myanmar'},
    'VN': {'lat': 14.05, 'lng': 108.27, 'name': 'Vietnam'},
    'PH': {'lat': 12.87, 'lng': 121.77, 'name': 'Philippines'},
    'MY': {'lat': 4.21, 'lng': 101.97, 'name': 'Malaysia'},
    'SG': {'lat': 1.35, 'lng': 103.81, 'name': 'Singapore'},
    'NZ': {'lat': -40.90, 'lng': 174.88, 'name': 'New Zealand'},
    'GR': {'lat': 39.07, 'lng': 21.82, 'name': 'Greece'},
    'IT': {'lat': 41.87, 'lng': 12.56, 'name': 'Italy'},
    'ES': {'lat': 40.46, 'lng': -3.74, 'name': 'Spain'},
    'PL': {'lat': 51.91, 'lng': 19.14, 'name': 'Poland'},
    'SE': {'lat': 60.12, 'lng': 18.64, 'name': 'Sweden'},
    'NO': {'lat': 60.47, 'lng': 8.46, 'name': 'Norway'},
    'FI': {'lat': 61.92, 'lng': 25.74, 'name': 'Finland'},
    'NL': {'lat': 52.13, 'lng': 5.29, 'name': 'Netherlands'},
    'BE': {'lat': 50.50, 'lng': 4.46, 'name': 'Belgium'},
    'CH': {'lat': 46.81, 'lng': 8.22, 'name': 'Switzerland'},
    'AT': {'lat': 47.51, 'lng': 14.55, 'name': 'Austria'},
    'CZ': {'lat': 49.81, 'lng': 15.47, 'name': 'Czech Republic'},
    'HU': {'lat': 47.16, 'lng': 19.50, 'name': 'Hungary'},
    'RO': {'lat': 45.94, 'lng': 24.96, 'name': 'Romania'},
    'BG': {'lat': 42.73, 'lng': 25.48, 'name': 'Bulgaria'},
    'RS': {'lat': 44.01, 'lng': 21.00, 'name': 'Serbia'},
    'HR': {'lat': 45.10, 'lng': 15.20, 'name': 'Croatia'},
    'TW': {'lat': 23.69, 'lng': 120.96, 'name': 'Taiwan'},
}


class GlobalWatchData:
    def __init__(self):
        self.events = []
        self.regions = {}
        self.last_update = time.time()
        self._init_regions()
        self._start_fetchers()

    def _init_regions(self):
        for code, info in COUNTRY_COORDS.items():
            self.regions[code] = {
                'code': code,
                'name': info['name'],
                'lat': info['lat'],
                'lng': info['lng'],
                'score': 0,
                'events': [],
                'categories': {'news': 0, 'earthquake': 0, 'conflict': 0, 'tech': 0}
            }

    def _start_fetchers(self):
        def fetch_loop():
            while True:
                self._fetch_earthquakes()
                self._fetch_news()
                self._calculate_scores()
                self.last_update = time.time()
                socketio.emit('update', {'events': self.events, 'regions': self.regions, 'timestamp': self.last_update})
                time.sleep(60)

        thread = threading.Thread(target=fetch_loop, daemon=True)
        thread.start()
        self._fetch_earthquakes()
        self._fetch_news()
        self._calculate_scores()

    def _fetch_earthquakes(self):
        try:
            resp = requests.get(USGS_API, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                self.events = [e for e in self.events if e.get('category') != 'earthquake']
                for quake in data.get('features', [])[:20]:
                    props = quake['properties']
                    coords = quake['geometry']['coordinates']
                    event = {
                        'id': f"quake_{quake['id']}",
                        'category': 'earthquake',
                        'title': f"M{props['mag']} - {props['place']}",
                        'description': props.get('tsunami', 0) == 1 and 'Tsunami warning' or 'No tsunami warning',
                        'lat': coords[1],
                        'lng': coords[0],
                        'depth': coords[2],
                        'magnitude': props['mag'],
                        'source': 'USGS',
                        'url': props.get('url', ''),
                        'time': props['time'],
                        'severity': 'critical' if props['mag'] >= 6 else 'high' if props['mag'] >= 5 else 'medium'
                    }
                    self.events.append(event)
                    self._assign_to_region(event)
        except Exception as e:
            print(f"Earthquake fetch error: {e}")

    def _fetch_news(self):
        if not NEWS_API_KEY:
            self._generate_demo_news()
            return
        
        try:
            categories = ['world', 'technology', 'politics', 'business']
            for cat in categories:
                url = f'https://newsapi.org/v2/top-headlines?category={cat}&language=en&pageSize=10&apiKey={NEWS_API_KEY}'
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    for article in data.get('articles', []):
                        if not article.get('title'):
                            continue
                        lat, lng = self._extract_coords(article)
                        if lat and lng:
                            category = self._categorize_news(article)
                            event = {
                                'id': f"news_{hash(article['url'])}",
                                'category': category,
                                'title': article['title'][:100],
                                'description': article.get('description', '')[:200] or '',
                                'lat': lat,
                                'lng': lng,
                                'source': article.get('source', {}).get('name', 'Unknown'),
                                'url': article.get('url', ''),
                                'image': article.get('urlToImage', ''),
                                'time': int(time.time()) - 3600,
                                'severity': self._assess_severity(article['title'], article.get('description', ''))
                            }
                            self.events.append(event)
                            self._assign_to_region(event)
        except Exception as e:
            print(f"News fetch error: {e}")
            self._generate_demo_news()

    def _generate_demo_news(self):
        demo_events = [
            {'lat': 31.76, 'lng': 35.21, 'title': 'Middle East tensions escalate', 'category': 'politics', 'severity': 'high'},
            {'lat': 52.52, 'lng': 13.40, 'title': 'Tech summit addresses AI regulation', 'category': 'tech', 'severity': 'medium'},
            {'lat': 55.75, 'lng': 37.61, 'title': 'Diplomatic discussions continue', 'category': 'politics', 'severity': 'medium'},
            {'lat': 39.90, 'lng': 116.40, 'title': 'Economic indicators show growth', 'category': 'business', 'severity': 'low'},
            {'lat': 35.67, 'lng': 139.65, 'title': 'New technology partnership announced', 'category': 'tech', 'severity': 'low'},
            {'lat': 51.50, 'lng': -0.12, 'title': 'Parliamentary session underway', 'category': 'politics', 'severity': 'medium'},
            {'lat': -33.86, 'lng': 151.20, 'title': 'Regional trade agreement signed', 'category': 'business', 'severity': 'medium'},
            {'lat': 25.20, 'lng': 55.27, 'title': 'Infrastructure development continues', 'category': 'business', 'severity': 'low'},
            {'lat': -23.55, 'lng': -46.63, 'title': 'Environmental initiative launched', 'category': 'world', 'severity': 'low'},
            {'lat': 28.61, 'lng': 77.20, 'title': 'Digital transformation push', 'category': 'tech', 'severity': 'medium'},
        ]
        for i, ev in enumerate(demo_events):
            event = {
                'id': f"demo_{i}",
                'category': ev['category'],
                'title': ev['title'],
                'description': '',
                'lat': ev['lat'],
                'lng': ev['lng'],
                'source': 'Demo Feed',
                'time': int(time.time()) - (i * 300),
                'severity': ev['severity']
            }
            self.events.append(event)
            self._assign_to_region(event)

    def _extract_coords(self, article):
        title = (article.get('title', '') + ' ' + article.get('description', '')).lower()
        
        location_map = {
            'israel': (31.04, 34.85), 'gaza': (31.35, 34.30), 'palestine': (31.95, 35.15),
            'ukraine': (48.37, 31.16), 'russia': (61.52, 105.31), 'moscow': (55.75, 37.61),
            'china': (35.86, 104.19), 'beijing': (39.90, 116.40),
            'iran': (32.42, 53.68), 'tehran': (35.68, 51.38),
            'usa': (37.09, -95.71), 'united states': (37.09, -95.71), 'washington': (38.90, -77.03),
            'uk': (55.37, -3.43), 'britain': (55.37, -3.43), 'london': (51.50, -0.12),
            'france': (46.22, 2.21), 'paris': (48.85, 2.35),
            'germany': (51.16, 10.45), 'berlin': (52.52, 13.40),
            'japan': (36.20, 138.25), 'tokyo': (35.67, 139.65),
            'india': (20.59, 78.96), 'delhi': (28.61, 77.20),
            'brazil': (-14.23, -51.92), 'sao paulo': (-23.55, -46.63),
            'australia': (-25.27, 133.77), 'sydney': (-33.86, 151.20),
            'south korea': (35.90, 127.76), 'seoul': (37.56, 126.97),
            'taiwan': (23.69, 120.96), 'taipei': (25.03, 121.56),
            'middle east': (29.30, 47.50),
            'europe': (48.85, 9.18),
            'africa': (1.28, 38.74),
            'asia': (35.86, 104.19),
        }
        
        for loc, coords in location_map.items():
            if loc in title:
                return coords
        return None, None

    def _categorize_news(self, article):
        title = (article.get('title', '') + ' ' + article.get('description', '')).lower()
        
        if any(w in title for w in ['war', 'conflict', 'attack', 'military', 'troops', 'battle', 'strike']):
            return 'conflict'
        elif any(w in title for w in ['ai', 'tech', 'startup', 'software', 'google', 'apple', 'microsoft', 'nvidia', 'cryptocurrency', 'bitcoin']):
            return 'tech'
        elif any(w in title for w in ['earthquake', 'flood', 'storm', 'hurricane', 'disaster', 'tsunami']):
            return 'disaster'
        else:
            return 'news'

    def _assess_severity(self, title, desc):
        text = (title + ' ' + desc).lower()
        critical = ['war', 'attack', 'killed', 'death', 'disaster', 'crisis', 'breaking']
        high = ['conflict', 'tension', 'threat', 'warning', 'emergency']
        
        if any(w in text for w in critical):
            return 'critical'
        elif any(w in text for w in high):
            return 'high'
        elif 'moderate' in text or 'concern' in text:
            return 'medium'
        return 'low'

    def _assign_to_region(self, event):
        lat, lng = event.get('lat'), event.get('lng')
        if lat is None or lng is None:
            return
        
        for code, region in self.regions.items():
            rlat, rlng = region['lat'], region['lng']
            distance = ((lat - rlat)**2 + (lng - rlng)**2)**0.5
            if distance < 30:
                region['events'].append(event['id'])
                region['categories'][event['category']] = region['categories'].get(event['category'], 0) + 1
                event['region'] = code

    def _calculate_scores(self):
        for region in self.regions.values():
            base_score = len(region['events']) * 5
            
            for event in region['events']:
                ev = next((e for e in self.events if e['id'] == event), None)
                if ev:
                    if ev.get('severity') == 'critical':
                        base_score += 40
                    elif ev.get('severity') == 'high':
                        base_score += 25
                    elif ev.get('severity') == 'medium':
                        base_score += 10
                    
                    if ev.get('category') == 'conflict':
                        base_score += 15
                    elif ev.get('category') == 'earthquake':
                        base_score += 20
            
            region['score'] = min(100, base_score)

    def get_events(self, category=None, lat=None, lng=None, radius=500):
        events = self.events
        if category:
            events = [e for e in events if e.get('category') == category]
        if lat is not None and lng is not None:
            filtered = []
            for e in events:
                if 'lat' in e and 'lng' in e:
                    dist = ((e['lat'] - lat)**2 + (e['lng'] - lng)**2)**0.5
                    if dist <= radius:
                        filtered.append(e)
            events = filtered
        return sorted(events, key=lambda x: x.get('time', 0), reverse=True)

    def get_regions(self):
        return list(self.regions.values())

    def get_region(self, code):
        return self.regions.get(code.upper())


data = GlobalWatchData()


def _load_static_files():
    global HTML_CONTENT, JS_CONTENT, SERVICES_CONTENT
    with open('index.html', 'r') as f:
        HTML_CONTENT = f.read()
    with open('app.js', 'r') as f:
        JS_CONTENT = f.read()
    with open('services.js', 'r') as f:
        SERVICES_CONTENT = f.read()


_load_static_files()


@app.route('/health')
def health():
    return jsonify({"status": "ok", "timestamp": time.time()})


@app.route('/api/events')
def get_events():
    category = request.args.get('category')
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    radius = request.args.get('radius', default=500, type=float)
    return jsonify(data.get_events(category, lat, lng, radius))


@app.route('/api/regions')
def get_regions():
    return jsonify(data.get_regions())


@app.route('/api/regions/<code>')
def get_region(code):
    region = data.get_region(code)
    if region:
        return jsonify(region)
    return jsonify({"error": "Region not found"}), 404


@app.route('/api/stats')
def get_stats():
    events = data.events
    return jsonify({
        'total': len(events),
        'by_category': {
            'news': len([e for e in events if e.get('category') == 'news']),
            'tech': len([e for e in events if e.get('category') == 'tech']),
            'conflict': len([e for e in events if e.get('category') == 'conflict']),
            'earthquake': len([e for e in events if e.get('category') == 'earthquake']),
        },
        'by_severity': {
            'critical': len([e for e in events if e.get('severity') == 'critical']),
            'high': len([e for e in events if e.get('severity') == 'high']),
            'medium': len([e for e in events if e.get('severity') == 'medium']),
            'low': len([e for e in events if e.get('severity') == 'low']),
        },
        'last_update': data.last_update
    })


@app.route('/')
def index():
    return HTML_CONTENT, 200, {'Content-Type': 'text/html'}


@app.route('/app.js')
def app_js():
    return JS_CONTENT, 200, {'Content-Type': 'application/javascript'}


@app.route('/services.js')
def services_js():
    return SERVICES_CONTENT, 200, {'Content-Type': 'application/javascript'}


@socketio.on('connect')
def handle_connect():
    emit('update', {'events': data.events, 'regions': data.regions, 'timestamp': data.last_update})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)
