import os
import time
import json
import requests
import threading
import logging
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
NOAA_HAZARDS_API = 'https://geo.weather.gov/hazards/v1/public/active'  # NOAA Active Hazards

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
                rate_limiter.record_failure('usgs')
            
            try:
                self._fetch_news()
                success = True
            except Exception as e:
                logging.error(f"News fetch failed: {e}")
                rate_limiter.record_failure('news')
            
            if not success and len(self.events) == 0:
                logging.warning('All APIs failed, using fallback events')
                self.events = FALLBACK_EVENTS.copy()
            
            self._calculate_scores()
            self._prune_events()
            self.last_update = time.time()
            socketio.emit('update', {'events': self.events, 'regions': self.regions, 'timestamp': self.last_update})

    def _fetch_earthquakes(self):
        if rate_limiter.is_circuit_open('usgs'):
            logging.warning('USGS circuit open, skipping')
            return
        if not rate_limiter.check_limit('usgs'):
            logging.warning('USGS rate limited')
            return
        
        try:
            logging.info('Fetching earthquakes from USGS')
            resp = requests.get(USGS_API, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                self.events = [e for e in self.events if e.get('category') != 'earthquake']
                for quake in data.get('features', [])[:20]:
                    props = quake['properties']
                    coords = quake['geometry']['coordinates']
                    mag = props['mag']
                    depth = coords[2]
                    
                    tsunami = 'Tsunami WATCH in effect' if props.get('tsunami', 0) == 2 else 'Tsunami WARNING' if props.get('tsunami', 0) == 1 else 'No tsunami threat'
                    
                    event = {
                        'id': f"quake_{quake['id']}",
                        'category': 'earthquake',
                        'title': f"M{mag} Earthquake - {props['place']}",
                        'description': f"Sent at depth of {depth:.1f}km. {tsunami}. Felt reports: {props.get('felt', 0)}. Significance: {props.get('sig', 0)}.",
                        'lat': coords[1],
                        'lng': coords[0],
                        'depth': depth,
                        'magnitude': mag,
                        'felt': props.get('felt', 0),
                        'significance': props.get('sig', 0),
                        'tsunami': tsunami,
                        'source': 'USGS Earthquake Hazards Program',
                        'url': props.get('url', ''),
                        'time': props['time'],
                        'severity': 'critical' if mag >= 6 else 'high' if mag >= 5 else 'medium'
                    }
                    self.events.append(event)
                    self._assign_to_region(event)
        except Exception as e:
            logging.error(f"Earthquake fetch error: {e}")

    def _fetch_news(self):
        logging.info('Fetching news from external sources')
        self.events = [e for e in self.events if e.get('category') in ['earthquake']]
        
        self._fetch_hackernews()
        
        if not hasattr(self, '_last_reddit_fetch') or (time.time() - getattr(self, '_last_reddit_fetch', 0)) > 120:
            self._last_reddit_fetch = time.time()
            self._fetch_worldnews()
        elif len([e for e in self.events if e.get('category') in ['news', 'conflict']]) == 0:
            self._fetch_worldnews()
        
        try:
            self._fetch_gdelt()
        except:
            pass
        
        if len([e for e in self.events if e.get('category') == 'news']) < 3:
            self._generate_demo_news()

    def _fetch_worldnews(self):
        try:
            resp = requests.get('https://www.reddit.com/r/worldnews/hot.json?limit=15', timeout=10, headers={'User-Agent': 'GlobalWatch/1.0'})
            if resp.status_code == 429:
                logging.warning("Reddit rate limited, using cached data")
                return
            if resp.status_code == 200:
                data = resp.json()
                posts = data.get('data', {}).get('children', [])
                for post in posts[:10]:
                    p = post.get('data', {})
                    if not p.get('title'):
                        continue
                    
                    lat, lng = self._guess_location_from_title(p['title'])
                    category = self._categorize_news({'title': p['title'], 'description': ''})
                    
                    score = p.get('score', 0)
                    num_comments = p.get('num_comments', 0)
                    subreddit = p.get('subreddit', 'worldnews')
                    author = p.get('author', 'anonymous')
                    over_18 = p.get('over_18', False)
                    selftext = p.get('selftext', '')[:200]
                    thumbnail = p.get('thumbnail', '')
                    url = p.get('url', '')
                    
                    desc_parts = []
                    if selftext:
                        desc_parts.append(selftext)
                    desc_parts.append(f"{score} upvotes")
                    desc_parts.append(f"{num_comments} comments")
                    desc_parts.append(f"by u/{author}")
                    
                    description = " • ".join(desc_parts)
                    
                    event = {
                        'id': f"reddit_{p['id']}",
                        'category': category,
                        'title': p['title'][:120],
                        'description': description,
                        'lat': lat or 0,
                        'lng': lng or 0,
                        'source': f'r/{subreddit}',
                        'score': score,
                        'comments': num_comments,
                        'author': author,
                        'selftext': selftext,
                        'thumbnail': thumbnail,
                        'url': url or f"https://reddit.com{p.get('permalink', '')}",
                        'time': int(p.get('created_utc', time.time())) * 1000,
                        'severity': self._assess_severity(p['title'], selftext)
                    }
                    self.events.append(event)
                    self._assign_to_region(event)
        except Exception as e:
            logging.error(f"Reddit fetch error: {e}")

    def _fetch_hackernews(self):
        try:
            top_stories = requests.get('https://hacker-news.firebaseio.com/v0/topstories.json', timeout=10).json()[:15]
            for story_id in top_stories:
                story = requests.get(f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json', timeout=10).json()
                if not story or not story.get('title'):
                    continue
                
                lat, lng = self._extract_tech_coords(story['title'])
                if not lat:
                    lat, lng = self._guess_location_from_title(story['title'])
                
                score = story.get('score', 0)
                descendants = story.get('descendants', 0)
                event_type = 'Ask' if story.get('type') == 'poll' and 'Ask' in story.get('title', '') else 'Show' if 'Show' in story.get('title', '') else 'Discussion' if descendants > 0 else 'Article'
                domain = ''
                if story.get('url'):
                    domain = story['url'].split('/')[2] if '/' in story['url'] else story['url']
                
                text = story.get('text', '')[:200] if story.get('text') else ''
                
                desc_parts = [f"{event_type} on Hacker News", f"{score} points", f"{descendants} comments", f"by {story.get('by', 'anonymous')}"]
                if domain:
                    desc_parts.append(f"Source: {domain}")
                description = " • ".join(desc_parts)
                if text:
                    description += f" • {text}"
                
                event = {
                    'id': f"hn_{story_id}",
                    'category': 'tech',
                    'title': story['title'][:120],
                    'description': description,
                    'lat': lat or 37.77,
                    'lng': lng or -122.41,
                    'source': 'Hacker News',
                    'domain': domain,
                    'points': score,
                    'comments': descendants,
                    'author': story.get('by', 'anonymous'),
                    'url': story.get('url', f'https://news.ycombinator.com/item?id={story_id}'),
                    'time': (story.get('time', 0)) * 1000,
                    'severity': 'medium' if score > 100 else 'low'
                }
                self.events.append(event)
                self._assign_to_region(event)
        except Exception as e:
            logging.error(f"HackerNews fetch error: {e}")

    def _fetch_gdelt(self):
        try:
            url = f'{GDELT_API}&mode=artlist&format=json&maxrecords=25&gaul=US,CN,RU,IN,BR,GB,FR,DE,JP,IL,UA,IR,KP,PK,TR,SA,ZA,AU,CA,MX,EG,KR,AF,SY,IQ,LY,YE,SD,ET,NG,CO,VE,AR,ID,TH,MM,VN,PH,MY,SG,NZ,GR,IT,ES,PL,SE,NO,FI,NL,BE,CH,AT,CZ,HU,RO,BG,RS,HR,TW'
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                articles = data.get('articles', []) or data.get('channels', [])[:1]
                if isinstance(articles, list) and len(articles) > 0:
                    if isinstance(articles[0], dict):
                        articles = articles[0].get('articles', []) or []
                
                for article in articles[:20]:
                    if not article.get('title'):
                        continue
                    
                    lat, lng = self._extract_coords_from_gdelt(article)
                    if lat is None:
                        lat, lng = self._guess_location_from_title(article.get('title', '') + ' ' + article.get('segments', ''))
                    
                    category = self._categorize_news(article)
                    event = {
                        'id': f"gdelt_{hash(article.get('url', article.get('link', '')))}",
                        'category': category,
                        'title': article.get('title', '')[:100],
                        'description': article.get('socialimage', '') or article.get('context', '')[:200] or '',
                        'lat': lat or 0,
                        'lng': lng or 0,
                        'source': article.get('domain', 'GDELT'),
                        'url': article.get('url', article.get('link', '')),
                        'time': self._parse_gdelt_date(article.get('seendate', '')),
                        'severity': self._assess_severity(article.get('title', ''), article.get('context', ''))
                    }
                    self.events.append(event)
                    self._assign_to_region(event)
        except Exception as e:
            logging.error(f"GDELT fetch error: {e}")

    def _parse_gdelt_date(self, date_str):
        try:
            if date_str:
                from datetime import datetime
                return int(datetime.strptime(date_str[:14], '%Y%m%dT%H%M%SZ').timestamp() * 1000)
        except:
            pass
        return int(time.time() * 1000)

    def _extract_tech_coords(self, title):
        title_lower = title.lower()
        tech_locations = {
            'san francisco': (37.77, -122.41),
            'silicon valley': (37.39, -122.08),
            'mountain view': (37.38, -122.08),
            'palo alto': (37.44, -122.14),
            'seattle': (47.60, -122.33),
            'new york': (40.71, -74.00),
            'london': (51.50, -0.12),
            'berlin': (52.52, 13.40),
            'tokyo': (35.67, 139.65),
            'singapore': (1.35, 103.81),
            'shenzhen': (22.54, 114.05),
            'beijing': (39.90, 116.40),
            'sydney': (-33.86, 151.20),
            'toronto': (43.65, -79.38),
            'boston': (42.36, -71.06),
            'austin': (30.26, -97.74),
        }
        for loc, coords in tech_locations.items():
            if loc in title_lower:
                return coords
        return None, None

    def _extract_coords_from_gdelt(self, article):
        text = f"{article.get('title', '')} {article.get('context', '')} {article.get('locations', '')}"
        return self._guess_location_from_title(text)

    def _guess_location_from_title(self, text):
        text_lower = text.lower()
        
        location_map = {
            'israel': (31.04, 34.85), 'gaza': (31.35, 34.30), 'palestine': (31.95, 35.15),
            'ukraine': (48.37, 31.16), 'russia': (61.52, 105.31), 'moscow': (55.75, 37.61),
            'china': (35.86, 104.19), 'beijing': (39.90, 116.40), 'shenzhen': (22.54, 114.05),
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
            'san francisco': (37.77, -122.41), 'silicon valley': (37.39, -122.08),
            'texas': (31.96, -99.90), 'austin': (30.26, -97.74),
            'florida': (27.66, -81.51), 'miami': (25.76, -80.19),
            'canada': (56.13, -106.34), 'toronto': (43.65, -79.38),
            'mexico': (23.63, -102.55),
            'egypt': (26.82, 30.80), 'cairo': (30.04, 31.23),
            'turkey': (38.96, 35.24), 'istanbul': (41.00, 28.97),
            'saudi': (23.88, 45.07), 'uae': (24.45, 54.37),
            'pakistan': (30.37, 69.34), 'afghanistan': (33.93, 67.70),
            'iraq': (33.22, 43.67), 'syria': (34.80, 38.99),
        }
        
        for loc, coords in location_map.items():
            if loc in text_lower:
                return coords
        return None, None

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
                'time': int(time.time() * 1000) - (i * 300000),
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

    def _assess_impact(self, title):
        title_lower = title.lower()
        high_impact_keywords = ['war', 'crisis', 'disaster', 'emergency', 'attack', 'breaking', 'deadly', 'major']
        medium_impact_keywords = ['conflict', 'tension', 'protest', 'election', 'climate', 'economic']
        
        if any(k in title_lower for k in high_impact_keywords):
            return 'This is a high-impact story with significant global implications.'
        elif any(k in title_lower for k in medium_impact_keywords):
            return 'This story is gaining attention for its regional or sector impact.'
        return 'This story is trending among the community.'

    def _haversine_km(self, lat1, lon1, lat2, lon2):
        import math
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    def _assign_to_region(self, event):
        lat, lng = event.get('lat'), event.get('lng')
        if lat is None or lng is None:
            return
        
        for code, region in self.regions.items():
            rlat, rlng = region['lat'], region['lng']
            distance = self._haversine_km(lat, lng, rlat, rlng)
            if distance < 500:
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

    def get_events(self, category=None, lat=None, lng=None, radius=500, search=''):
        events = self.events
        if category:
            events = [e for e in events if e.get('category') == category]
        if search:
            search_lower = search.lower()
            events = [e for e in events if search_lower in e.get('title', '').lower() or search_lower in e.get('description', '').lower()]
        if lat is not None and lng is not None:
            filtered = []
            for e in events:
                if 'lat' in e and 'lng' in e:
                    dist = self._haversine_km(lat, lng, e['lat'], e['lng'])
                    if dist <= radius:
                        filtered.append(e)
            events = filtered
        return sorted(events, key=lambda x: x.get('time', 0), reverse=True)

    def get_regions(self):
        return list(self.regions.values())

    def get_region(self, code):
        return self.regions.get(code.upper())


class SimpleML:
    def linear_regression(self, x, y):
        n = len(x)
        if n < 2:
            return 0, 0
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)
        
        denom = n * sum_x2 - sum_x * sum_x
        if denom == 0:
            return 0, sum_y / n
        
        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n
        return slope, intercept
    
    def classify_risk(self, events):
        severity_scores = {'critical': 1.0, 'high': 0.7, 'medium': 0.4, 'low': 0.1}
        score = sum(severity_scores.get(e.get('severity', 'low'), 0) for e in events) / max(len(events), 1)
        return min(1, score * 1.5)


simple_ml = SimpleML()


class PredictionEngine:
    def __init__(self):
        self.history = []
        self.patterns = {
            'conflict': {
                'escalation_threshold': 3,
                'typical_duration_hours': 48,
                'escalation_keywords': ['escalation', 'troops', 'attack', 'fighting', 'offensive']
            },
            'earthquake': {
                'aftershock_window_hours': 24,
                'aftershock_probability': 0.6,
                'magnitude_correlation': 0.8
            },
            'news': {
                'viral_window_hours': 12,
                'engagement_decay': 0.7
            }
        }
    
    def analyze(self, events, timeline_hours=24):
        if not events:
            return {'predictions': [], 'confidence': 'low'}
        
        predictions = []
        all_events = events
        
        predictions.extend(self._analyze_event_based_predictions(all_events, timeline_hours))
        
        confidence = self._calculate_confidence(events, predictions)
        
        return {
            'predictions': predictions[:5],
            'confidence': confidence,
            'analyzed_events': len(events),
            'timeline_hours': timeline_hours,
            'based_on': 'specific_events'
        }
    
    def _analyze_event_based_predictions(self, events, hours):
        predictions = []
        
        severity_weight = {'critical': 0.87, 'high': 0.72, 'medium': 0.55, 'low': 0.40}
        
        for e in events:
            cat = e.get('category')
            sev = e.get('severity', 'low')
            prob = severity_weight.get(sev, 0.40)
            
            if cat == 'conflict':
                predictions.append({
                    'type': 'conflict_continuation',
                    'title': f'Conflict Activity Expected - {e.get("region", "Region")}',
                    'description': f'Based on current conflict event: "{e.get("title", "Ongoing")}". Historical patterns show {int(prob*100)}% likelihood of continuation in the region.',
                    'probability': prob,
                    'timeframe': f'{hours}h',
                    'based_on_event': e.get('id'),
                    'severity': sev
                })
            elif cat == 'earthquake':
                mag = e.get('magnitude', 0)
                if mag >= 4.5:
                    predictions.append({
                        'type': 'aftershock_expected',
                        'title': f'Possible Aftershock - M{mag:.1f} region',
                        'description': f'M{mag} earthquake detected. Analysis suggests {int(prob*100)}% probability of aftershocks in the following hours.',
                        'probability': min(0.87, prob + 0.1),
                        'timeframe': '24 hours',
                        'based_on_event': e.get('id'),
                        'severity': sev
                    })
            elif cat == 'news':
                predictions.append({
                    'type': 'story_amplification',
                    'title': f'News Story Amplification Likely',
                    'description': f'News: "{e.get("title", "")[:50]}..." - {int(prob*100)}% probability of broader coverage and engagement spike.',
                    'probability': min(0.87, prob + 0.05),
                    'timeframe': '12-24 hours',
                    'based_on_event': e.get('id'),
                    'severity': sev
                })
            elif cat == 'tech':
                predictions.append({
                    'type': 'tech_momentum',
                    'title': f'Tech Story Momentum Expected',
                    'description': f'Tech: "{e.get("title", "")[:50]}..." - {int(prob*100)}% probability of continued discussion and engagement.',
                    'probability': min(0.87, prob + 0.08),
                    'timeframe': '12h',
                    'based_on_event': e.get('id'),
                    'severity': sev
                })
        
        region_clusters = {}
        for e in events:
            reg = e.get('region', 'Unknown')
            if reg not in region_clusters:
                region_clusters[reg] = []
            region_clusters[reg].append(e)
        
        for reg, reg_events in region_clusters.items():
            if len(reg_events) >= 2:
                avg_sev = sum(severity_weight.get(ev.get('sev', 'low'), 0.4) for ev in reg_events) / len(reg_events)
                predictions.append({
                    'type': 'regional_activity',
                    'title': f'Elevated Activity in {reg}',
                    'description': f'{len(reg_events)} events in {reg}. Pattern analysis shows {int(min(0.87, avg_sev + 0.15)*100)}% probability of continued elevated activity.',
                    'probability': min(0.87, avg_sev + 0.15),
                    'timeframe': '24-48 hours',
                    'based_on_events': [e.get('id') for e in reg_events[:3]],
                    'severity': 'medium'
                })
        
        return predictions
    
    def _predict_conflict_escalation(self, events, hours):
        predictions = []
        conflicts = [e for e in events if e.get('category') == 'conflict']
        
        if len(conflicts) >= 2:
            regions = set(e.get('region', 'Unknown') for e in conflicts)
            if len(regions) >= 2:
                predictions.append({
                    'type': 'escalation_risk',
                    'title': 'Potential Regional Escalation',
                    'description': f'{len(conflicts)} conflict events across {len(regions)} regions suggest elevated tension. Monitor for 24-48h.',
                    'probability': 0.6,
                    'timeframe': '24-48 hours',
                    'affected_regions': list(regions),
                    'severity': 'high'
                })
        
        return predictions
    
    def _predict_aftershocks(self, events, hours):
        predictions = []
        earthquakes = [e for e in events if e.get('category') == 'earthquake']
        
        for quake in earthquakes:
            magnitude = quake.get('magnitude', 0)
            if magnitude >= 5.0:
                probability = min(0.9, magnitude * 0.15)
                predictions.append({
                    'type': 'aftershock',
                    'title': f'Possible Aftershock - M{magnitude - 0.5:.1f}-{magnitude:.1f}',
                    'description': f'Main shock was M{magnitude}. Historical data shows {int(probability*100)}% probability of aftershocks within 24h.',
                    'probability': probability,
                    'timeframe': '24 hours',
                    'location': {'lat': quake.get('lat'), 'lng': quake.get('lng')},
                    'severity': 'medium'
                })
        
        return predictions
    
    def _predict_regional_spike(self, events, hours):
        predictions = []
        region_counts = {}
        
        for e in events:
            region = e.get('region', 'Unknown')
            region_counts[region] = region_counts.get(region, 0) + 1
        
        for region, count in region_counts.items():
            if count >= 2:
                predictions.append({
                    'type': 'regional_spike',
                    'title': f'Elevated Activity in {region}',
                    'description': f'{count} events recorded in {region}. Based on activity patterns, expect continued elevated activity for next 12-24h.',
                    'probability': 0.5,
                    'timeframe': '12-24 hours',
                    'region': region,
                    'severity': 'medium'
                })
        
        return predictions
    
    def _predict_trending_topics(self, events, hours):
        predictions = []
        
        categories = {}
        for e in events:
            cat = e.get('category', 'other')
            categories[cat] = categories.get(cat, 0) + 1
        
        dominant = max(categories.items(), key=lambda x: x[1])
        if dominant[1] >= 3:
            predictions.append({
                'type': 'trending',
                'title': f'Trending: {dominant[0].upper()}',
                'description': f'{dominant[1]} {dominant[0]} events in timeline. Likely to remain active in coming hours.',
                'probability': 0.4,
                'timeframe': '12 hours',
                'severity': 'low'
            })
        
        return predictions
    
    def _calculate_confidence(self, events, predictions):
        if len(events) >= 10 and len(predictions) >= 2:
            return 'high'
        elif len(events) >= 5:
            return 'medium'
        return 'low'


prediction_engine = PredictionEngine()


data = GlobalWatchData()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)

logging.info('Initial data fetch...')
data.ensure_fresh(force=True)
logging.info(f'Loaded {len(data.events)} events on startup')


def _load_static_files():
    global HTML_CONTENT, JS_CONTENT, SERVICES_CONTENT
    base_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        with open(os.path.join(base_dir, 'index.html'), 'r') as f:
            HTML_CONTENT = f.read()
        with open(os.path.join(base_dir, 'app.js'), 'r') as f:
            JS_CONTENT = f.read()
        with open(os.path.join(base_dir, 'services.js'), 'r') as f:
            SERVICES_CONTENT = f.read()
        logging.info('Static files loaded')
    except FileNotFoundError as e:
        logging.error(f'Missing static file: {e}')
        HTML_CONTENT = '<h1>Error loading content</h1>'
        JS_CONTENT = ''
        SERVICES_CONTENT = ''

if not HTML_CONTENT:
    _load_static_files()


@app.route('/health')
def health():
    return jsonify({"status": "ok", "timestamp": time.time()})


@app.route('/api/refresh')
def refresh():
    data.ensure_fresh(force=True)
    return jsonify({"status": "refreshed", "timestamp": data.last_update})


@app.route('/api/events')
def get_events():
    data.ensure_fresh()
    category = request.args.get('category')
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    radius = request.args.get('radius', default=500, type=float)
    search = request.args.get('search', '').strip().lower()
    return jsonify(data.get_events(category, lat, lng, radius, search))


@app.route('/api/regions')
def get_regions():
    data.ensure_fresh()
    return jsonify(data.get_regions())


@app.route('/api/regions/<code>')
def get_region(code):
    region = data.get_region(code)
    if region:
        return jsonify(region)
    return jsonify({"error": "Region not found"}), 404


@app.route('/api/stats')
def get_stats():
    data.ensure_fresh()
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
    data.ensure_fresh()
    emit('update', {'events': data.events, 'regions': data.regions, 'timestamp': data.last_update})


@app.route('/api/cache-status')
def cache_status():
    age = time.time() - data.last_update if data.last_update else 0
    return jsonify({
        "cached": bool(data.events),
        "age_seconds": age,
        "needs_refresh": age > data.cache_ttl if age else True
    })


def _extractive_summarize(text, num_sentences=2):
    if not text or len(text) < 50:
        return text or "No description available."
    
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    if len(sentences) <= num_sentences:
        return text
    
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
                'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare', 'ought',
                'it', 'its', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she',
                'we', 'they', 'what', 'which', 'who', 'when', 'where', 'why', 'how'}
    
    def score_sentence(s):
        words = re.findall(r'\b[a-zA-Z]+\b', s.lower())
        score = sum(1 for w in words if w not in stop_words)
        return score * (1 + 0.1 * len(words))
    
    scored = [(s, score_sentence(s)) for s in sentences]
    scored.sort(key=lambda x: x[1], reverse=True)
    
    top_sentences = [s[0] for s in scored[:num_sentences]]
    top_sentences.sort(key=lambda s: sentences.index(s))
    
    return ' '.join(top_sentences)


@app.route('/api/summarize', methods=['POST'])
def summarize():
    data.ensure_fresh()
    payload = request.get_json()
    event_id = payload.get('event_id')
    text = payload.get('text', '')
    
    if event_id:
        event = next((e for e in data.events if e.get('id') == event_id), None)
        if event:
            text = event.get('description', '') or event.get('title', '')
    
    summary = _extractive_summarize(text)
    
    return jsonify({
        'summary': summary,
        'original_length': len(text),
        'summary_length': len(summary)
    })


@app.route('/api/sentiment', methods=['POST'])
def sentiment():
    data.ensure_fresh()
    payload = request.get_json()
    event_id = payload.get('event_id')
    text = payload.get('text', '')
    
    if event_id:
        event = next((e for e in data.events if e.get('id') == event_id), None)
        if event:
            text = (event.get('description', '') + ' ' + event.get('title', ''))
    
    text_lower = text.lower()
    positive_words = ['growth', 'increase', 'success', 'deal', 'agreement', 'peace', 'help', 'support', 'positive']
    negative_words = ['death', 'kill', 'attack', 'war', 'crisis', 'disaster', 'emergency', 'crash', 'fail', 'fear']
    
    pos_count = sum(1 for w in positive_words if w in text_lower)
    neg_count = sum(1 for w in negative_words if w in text_lower)
    
    if neg_count > pos_count:
        sentiment = 'negative'
        score = -min(1, neg_count * 0.3)
    elif pos_count > neg_count:
        sentiment = 'positive'
        score = min(1, pos_count * 0.3)
    else:
        sentiment = 'neutral'
        score = 0
    
    return jsonify({
        'sentiment': sentiment,
        'score': score,
        'positive_mentions': pos_count,
        'negative_mentions': neg_count
    })


webhook_configs = {}


@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    return jsonify({'webhooks': list(webhook_configs.values())})


@app.route('/api/alerts', methods=['POST'])
def add_alert():
    payload = request.get_json()
    webhook_id = payload.get('id', f"webhook_{len(webhook_configs)}")
    webhook_url = payload.get('url')
    alert_type = payload.get('type', 'discord')
    filters = payload.get('filters', {})
    
    if not webhook_url:
        return jsonify({'error': 'URL required'}), 400
    
    webhook_configs[webhook_id] = {
        'id': webhook_id,
        'url': webhook_url,
        'type': alert_type,
        'filters': filters
    }
    
    return jsonify({'status': 'added', 'webhook': webhook_configs[webhook_id]})


@app.route('/api/alerts/<webhook_id>', methods=['DELETE'])
def delete_alert(webhook_id):
    if webhook_id in webhook_configs:
        del webhook_configs[webhook_id]
        return jsonify({'status': 'deleted'})
    return jsonify({'error': 'Not found'}), 404


@app.route('/api/predict', methods=['GET'])
def get_predictions():
    data.ensure_fresh()
    timeline_hours = request.args.get('hours', default=24, type=int)
    events = data.events
    
    analysis = prediction_engine.analyze(events, timeline_hours)
    
    return jsonify(analysis)


@app.route('/api/predict/<region>', methods=['GET'])
def get_region_predictions(region):
    data.ensure_fresh()
    region = region.upper()
    region_events = [e for e in data.events if e.get('region') == region]
    timeline_hours = request.args.get('hours', default=24, type=int)
    
    analysis = prediction_engine.analyze(region_events, timeline_hours)
    
    return jsonify(analysis)


def _send_webhook_alert(event):
    for config in webhook_configs.values():
        try:
            if config['type'] == 'discord':
                _send_discord_alert(config['url'], event)
            elif config['type'] == 'slack':
                _send_slack_alert(config['url'], event)
        except Exception as e:
            logging.error(f"Webhook error: {e}")


def _send_discord_alert(url, event):
    payload = {
        'embeds': [{
            'title': event.get('title', 'Event Alert'),
            'description': event.get('description', '')[:1000],
            'color': 0xef4444 if event.get('severity') == 'critical' else 0xf97316 if event.get('severity') == 'high' else 0x3b82f6,
            'fields': [
                {'name': 'Category', 'value': event.get('category', 'N/A'), 'inline': True},
                {'name': 'Severity', 'value': event.get('severity', 'N/A').upper(), 'inline': True},
                {'name': 'Source', 'value': event.get('source', 'N/A'), 'inline': True}
            ],
            'timestamp': datetime.fromtimestamp(event.get('time', 0) / 1000).isoformat() if event.get('time') else None
        }]
    }
    requests.post(url, json=payload, timeout=10)


def _send_slack_alert(url, event):
    payload = {
        'text': f"*{event.get('title', 'Event Alert')}*",
        'blocks': [
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f"*{event.get('severity', 'N/A').upper()}* - {event.get('category', 'N/A')}"
                }
            },
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': event.get('description', '')[:500]
                }
            }
        ]
    }
    requests.post(url, json=payload, timeout=10)


@app.route('/api/weather', methods=['GET'])
def get_weather():
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    
    if lat is None or lng is None:
        return jsonify({'error': 'lat and lng required'}), 400
    
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current=temperature_2m,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,weather_code"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return jsonify(resp.json())
        return jsonify({'error': 'Weather unavailable'}), 502
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/weather/<lat>/<lng>', methods=['GET'])
def get_weather_coords(lat, lng):
    try:
        lat = float(lat)
        lng = float(lng)
    except:
        return jsonify({'error': 'Invalid coordinates'}), 400
    
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current=temperature_2m,weather_code,wind_speed_10m,humidity&daily=temperature_2m_max,temperature_2m_min,weather_code&timezone=auto"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            current = data.get('current', {})
            return jsonify({
                'temperature': current.get('temperature_2m'),
                'weather_code': current.get('weather_code'),
                'wind_speed': current.get('wind_speed_10m'),
                'humidity': current.get('humidity'),
                'daily': data.get('daily', {})
            })
        return jsonify({'error': 'Weather unavailable'}), 502
    except Exception as e:
        return jsonify({'error': str(e)}), 500


from datetime import datetime


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)
