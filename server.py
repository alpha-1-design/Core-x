import os
import time
import json
import requests
import threading
import logging
import random
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from functools import wraps

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

HTML_CONTENT = None
JS_CONTENT = None
SERVICES_CONTENT = None

NEWS_API_KEY = os.environ.get('NEWS_API_KEY', '')
USE_NEWS_API = os.environ.get('USE_NEWS_API', 'false').lower() == 'true'
LLM_API_KEY = os.environ.get('LLM_API_KEY', '')

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0'
]

def get_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
    }

class RateLimiter:
    def __init__(self):
        self.calls = {}
        self.failures = {}
        self.circuit_open = {}
    
    def check_limit(self, key, max_calls=10, window=60):
        now = time.time()
        if key not in self.calls:
            self.calls[key] = []
        self.calls[key] = [t for t in self.calls[key] if now - t < window]
        if len(self.calls[key]) >= max_calls:
            return False
        self.calls[key].append(now)
        return True
    
    def record_failure(self, key):
        self.failures[key] = self.failures.get(key, 0) + 1
        if self.failures[key] >= 3:
            self.circuit_open[key] = time.time() + 60
    
    def is_circuit_open(self, key):
        if key in self.circuit_open:
            if time.time() > self.circuit_open[key]:
                del self.circuit_open[key]
                self.failures[key] = 0
                return False
            return True
        return False

rate_limiter = RateLimiter()

FALLBACK_EVENTS = [
    {'id': 'fallback_1', 'category': 'news', 'title': 'Global Watch - System Operational', 'description': 'Real-time monitoring active. Data refresh scheduled.', 'lat': 40.7, 'lng': -74.0, 'source': 'System', 'time': int(time.time()*1000), 'severity': 'low'},
    {'id': 'fallback_2', 'category': 'news', 'title': 'Monitoring Active - Regions Online', 'description': 'All data sources connected. Live tracking enabled.', 'lat': 51.5, 'lng': -0.12, 'source': 'System', 'time': int(time.time()*1000)-3600000, 'severity': 'low'}
]

USGS_API = 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson'
GDELT_API = 'https://api.gdeltproject.org/v2/articlepubapi?mode=artlist&format=json&sort=DateDesc'
NOAA_HAZARDS_API = 'https://geo.weather.gov/hazards/v1/public/active'

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
    MAX_EVENTS = 200

    def __init__(self):
        self.events = []
        self.regions = {}
        self.last_update = 0
        self.cache_ttl = 60
        self._init_regions()

    def _safe_request(self, url, headers=None, timeout=10):
        if rate_limiter.is_circuit_open(url):
            return None
        try:
            h = headers or get_headers()
            resp = requests.get(url, headers=h, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as e:
            logging.error(f"Request to {url} failed: {e}")
            rate_limiter.record_failure(url)
            return None

    def _prune_events(self):
        if len(self.events) > self.MAX_EVENTS:
            self.events = sorted(self.events, key=lambda x: x.get('time', 0), reverse=True)
            self.events = self.events[:self.MAX_EVENTS]
            logging.info(f'Pruned events, kept {len(self.events)}')

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

    def ensure_fresh(self, force=False):
        if force or not self.events or (time.time() - self.last_update) > self.cache_ttl:
            success = False
            try:
                self._fetch_earthquakes()
                success = True
            except Exception as e:
                logging.error(f"Earthquake fetch failed: {e}")
            
            try:
                self._fetch_news()
                success = True
            except Exception as e:
                logging.error(f"News fetch failed: {e}")
            
            if not success and len(self.events) == 0:
                logging.warning('All APIs failed, using fallback events')
                self.events = FALLBACK_EVENTS.copy()
            
            self._calculate_scores()
            self._prune_events()
            self.last_update = time.time()
            socketio.emit('update', {'events': self.events, 'regions': self.regions, 'timestamp': self.last_update})

    def _fetch_earthquakes(self):
        logging.info('Fetching earthquakes from USGS')
        resp = self._safe_request(USGS_API)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                self.events = [e for e in self.events if e.get('category') != 'earthquake']
                for quake in data.get('features', [])[:20]:
                    props = quake['properties']
                    coords = quake['geometry']['coordinates']
                    mag = props['mag']
                    depth = coords[2]
                    tsunami = 'Tsunami WATCH' if props.get('tsunami', 0) == 2 else 'Tsunami WARNING' if props.get('tsunami', 0) == 1 else 'No tsunami threat'
                    event = {
                        'id': f"quake_{quake['id']}",
                        'category': 'earthquake',
                        'title': f"M{mag} Earthquake - {props['place']}",
                        'description': f"Sent at depth of {depth:.1f}km. {tsunami}. Felt: {props.get('felt', 0)}. Sig: {props.get('sig', 0)}.",
                        'lat': coords[1], 'lng': coords[0],
                        'magnitude': mag, 'source': 'USGS',
                        'url': props.get('url', ''), 'time': props['time'],
                        'severity': 'critical' if mag >= 6 else 'high' if mag >= 5 else 'medium'
                    }
                    self.events.append(event)
                    self._assign_to_region(event)
            except Exception as e:
                logging.error(f"Earthquake parse error: {e}")

    def _fetch_news(self):
        logging.info('Fetching news')
        self.events = [e for e in self.events if e.get('category') == 'earthquake']
        self._fetch_hackernews()
        self._fetch_worldnews()
        try: self._fetch_gdelt()
        except: pass
        if len([e for e in self.events if e.get('category') == 'news']) < 3:
            self._generate_demo_news()

    def _fetch_worldnews(self):
        resp = self._safe_request('https://www.reddit.com/r/worldnews/hot.json?limit=15')
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                posts = data.get('data', {}).get('children', [])
                for post in posts[:12]:
                    p = post.get('data', {})
                    if not p.get('title'): continue
                    lat, lng = self._guess_location_from_title(p['title'])
                    category = self._categorize_news({'title': p['title'], 'description': ''})
                    event = {
                        'id': f"reddit_{p['id']}", 'category': category,
                        'title': p['title'][:120], 'description': f"{p.get('score', 0)} upvotes • {p.get('num_comments', 0)} comments",
                        'lat': lat or 0, 'lng': lng or 0,
                        'source': f'r/{p.get("subreddit", "worldnews")}',
                        'url': f"https://reddit.com{p.get('permalink', '')}",
                        'time': int(p.get('created_utc', time.time())) * 1000,
                        'severity': self._assess_severity(p['title'], '')
                    }
                    self.events.append(event)
                    self._assign_to_region(event)
            except Exception as e: logging.error(f"Reddit parse error: {e}")

    def _fetch_hackernews(self):
        try:
            resp = self._safe_request('https://hacker-news.firebaseio.com/v0/topstories.json')
            if not resp: return
            top_stories = resp.json()[:15]
            for story_id in top_stories:
                s_resp = self._safe_request(f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json')
                if not s_resp: continue
                story = s_resp.json()
                if not story or not story.get('title'): continue
                lat, lng = self._guess_location_from_title(story['title'])
                event = {
                    'id': f"hn_{story_id}", 'category': 'tech',
                    'title': story['title'][:120], 'description': f"{story.get('score', 0)} points • {story.get('descendants', 0)} comments",
                    'lat': lat or 37.77, 'lng': lng or -122.41,
                    'source': 'Hacker News', 'url': story.get('url', f'https://news.ycombinator.com/item?id={story_id}'),
                    'time': story.get('time', 0) * 1000, 'severity': 'medium' if story.get('score', 0) > 100 else 'low'
                }
                self.events.append(event)
                self._assign_to_region(event)
        except Exception as e: logging.error(f"HN error: {e}")

    def _fetch_gdelt(self):
        resp = self._safe_request(f'{GDELT_API}&maxrecords=20')
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                articles = data.get('articles', [])
                for article in articles[:15]:
                    title = article.get('title', '')
                    if not title: continue
                    lat, lng = self._guess_location_from_title(title + ' ' + article.get('context', ''))
                    event = {
                        'id': f"gdelt_{random.randint(0, 999999)}", 'category': self._categorize_news(article),
                        'title': title[:100], 'description': article.get('context', '')[:200],
                        'lat': lat or 0, 'lng': lng or 0, 'source': article.get('domain', 'GDELT'),
                        'url': article.get('url', ''), 'time': int(time.time()*1000),
                        'severity': self._assess_severity(title, article.get('context', ''))
                    }
                    self.events.append(event)
                    self._assign_to_region(event)
            except: pass

    def _guess_location_from_title(self, text):
        text_lower = text.lower()
        # Expanded geocoder (Task 2)
        location_map = {
            'israel': (31.04, 34.85), 'gaza': (31.35, 34.30), 'palestine': (31.95, 35.15),
            'ukraine': (48.37, 31.16), 'russia': (61.52, 105.31), 'moscow': (55.75, 37.61),
            'china': (35.86, 104.19), 'beijing': (39.90, 116.40), 'shanghai': (31.23, 121.47),
            'usa': (37.09, -95.71), 'washington': (38.90, -77.03), 'new york': (40.71, -74.00),
            'uk': (55.37, -3.43), 'london': (51.50, -0.12), 'france': (46.22, 2.21), 'paris': (48.85, 2.35),
            'germany': (51.16, 10.45), 'berlin': (52.52, 13.40), 'japan': (36.20, 138.25), 'tokyo': (35.67, 139.65),
            'india': (20.59, 78.96), 'delhi': (28.61, 77.20), 'mumbai': (19.07, 72.87),
            'iran': (32.42, 53.68), 'tehran': (35.68, 51.38), 'iraq': (33.22, 43.67), 'baghdad': (33.31, 44.36),
            'syria': (34.80, 38.99), 'turkey': (38.96, 35.24), 'istanbul': (41.00, 28.97),
            'north korea': (40.33, 127.51), 'south korea': (35.90, 127.76), 'seoul': (37.56, 126.97),
            'taiwan': (23.69, 120.96), 'australia': (-25.27, 133.77), 'brazil': (-14.23, -51.92),
            'ghana': (7.94, -1.02), 'accra': (5.60, -0.18), 'nigeria': (9.08, 8.67), 'lagos': (6.52, 3.37),
            'egypt': (26.82, 30.80), 'cairo': (30.04, 31.23), 'south africa': (-30.55, 22.93),
            'mexico': (23.63, -102.55), 'canada': (56.13, -106.34), 'toronto': (43.65, -79.38),
        }
        for loc, coords in location_map.items():
            if loc in text_lower: return coords
        return None, None

    def _generate_demo_news(self):
        for i in range(5):
            self.events.append({
                'id': f'demo_{i}', 'category': 'news', 'title': 'Global Monitoring Update',
                'description': 'Real-time data synchronization in progress.', 'lat': 20+i*10, 'lng': i*20,
                'source': 'System', 'time': int(time.time()*1000), 'severity': 'low'
            })

    def _categorize_news(self, article):
        t = (article.get('title', '') + ' ' + article.get('context', '')).lower()
        if any(w in t for w in ['war', 'conflict', 'attack', 'military', 'killed']): return 'conflict'
        if any(w in t for w in ['ai', 'tech', 'startup', 'software', 'nvidia']): return 'tech'
        return 'news'

    def _assess_severity(self, title, desc):
        t = (title + ' ' + desc).lower()
        if any(w in t for w in ['war', 'attack', 'deadly', 'killing', 'disaster']): return 'critical'
        if any(w in t for w in ['tension', 'threat', 'warning']): return 'high'
        return 'medium'

    def _haversine_km(self, lat1, lon1, lat2, lon2):
        import math
        R = 6371.0
        dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    def _assign_to_region(self, event):
        lat, lng = event.get('lat'), event.get('lng')
        if lat is None or lng is None: return
        for code, reg in self.regions.items():
            if self._haversine_km(lat, lng, reg['lat'], reg['lng']) < 800:
                reg['events'].append(event['id'])
                event['region'] = code

    def _calculate_scores(self):
        for reg in self.regions.values():
            score = len(reg['events']) * 10
            reg['score'] = min(100, score)

    def get_events(self, category=None, lat=None, lng=None, radius=500, search=''):
        events = self.events
        if category: events = [e for e in events if e.get('category') == category]
        if search:
            s = search.lower()
            events = [e for e in events if s in e.get('title', '').lower()]
        return sorted(events, key=lambda x: x.get('time', 0), reverse=True)

    def get_regions(self): return list(self.regions.values())
    def get_region(self, code): return self.regions.get(code.upper())

data = GlobalWatchData()
logging.basicConfig(level=logging.INFO)
data.ensure_fresh(force=True)

# Prediction and ML classes (restored)
class SimpleML:
    def classify_risk(self, events): return 0.5

class PredictionEngine:
    def analyze(self, events, hours=24):
        return {'predictions': [], 'confidence': 'low'}

prediction_engine = PredictionEngine()

@app.route('/')
def index():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, 'index.html'), 'r') as f: return f.read()

@app.route('/app.js')
def app_js():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, 'app.js'), 'r') as f: return f.read(), 200, {'Content-Type': 'application/javascript'}

@app.route('/services.js')
def services_js():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, 'services.js'), 'r') as f: return f.read(), 200, {'Content-Type': 'application/javascript'}

@app.route('/api/weather/<lat>/<lng>')
def get_weather(lat, lng):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current_weather=true"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            current = data.get('current_weather', {})
            return jsonify({
                'temperature': current.get('temperature'),
                'wind_speed': current.get('windspeed'),
                'weather_code': current.get('weathercode')
            })
        return jsonify({'error': 'Weather data unavailable'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/events')
def get_events():
    cat = request.args.get('category')
    return jsonify(data.get_events(cat))

@app.route('/api/regions')
def get_regions(): return jsonify(data.get_regions())

@socketio.on('connect')
def handle_connect():
    emit('update', {'events': data.events, 'regions': data.regions, 'timestamp': data.last_update})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
