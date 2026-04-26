import os
import requests
from typing import List, Dict

SERPAPI_KEY = os.getenv('SERPAPI_KEY', '15ac2b2f9cc36da18e44a78b028cf924ca8c64f08a7c37772ae7dde184ca73d9')

# Country name/keyword → [lng, lat]
LOCATION_MAP = {
    # Explicit country names
    'united states': (-98, 39), 'usa': (-98, 39), 'u.s.': (-98, 39), 'u.s': (-98, 39), 'american': (-98, 39),
    'canada': (-96, 60), 'canadian': (-96, 60),
    'germany': (10, 51), 'german': (10, 51),
    'france': (2, 46), 'french': (2, 46),
    'united kingdom': (-2, 54), 'england': (-1.5, 52), 'british': (-2, 54), 'uk ': (-2, 54), ' uk': (-2, 54),
    'australia': (134, -25), 'australian': (134, -25),
    'china': (105, 35), 'chinese': (105, 35), 'beijing': (116.4, 39.9), 'shanghai': (121.5, 31.2),
    'india': (78, 22), 'indian': (78, 22),
    'japan': (138, 36), 'japanese': (138, 36), 'tokyo': (139.7, 35.7),
    'brazil': (-51, -14), 'brazilian': (-51, -14),
    'mexico': (-102, 24), 'mexican': (-102, 24),
    'south korea': (128, 37), 'korean': (128, 37), 'seoul': (126.9, 37.6),
    'russia': (105, 61), 'russian': (105, 61),
    'sweden': (18, 62), 'swedish': (18, 62),
    'norway': (15, 65), 'norwegian': (15, 65),
    'denmark': (10, 56), 'danish': (10, 56),
    'netherlands': (5, 52), 'dutch': (5, 52),
    'spain': (-3.7, 40.4), 'spanish': (-3.7, 40.4),
    'italy': (12.5, 42), 'italian': (12.5, 42),
    'switzerland': (8.2, 46.8), 'swiss': (8.2, 46.8),
    'israel': (34.8, 31.5), 'israeli': (34.8, 31.5),
    'singapore': (103.8, 1.3),
    'new zealand': (172, -41),
    'south africa': (25, -29),
    'argentina': (-64, -34),
    'belgium': (4.5, 50.5),
    'austria': (14.5, 47.5),
    'portugal': (-8.2, 39.4),
    'turkey': (35, 39),
    'saudi arabia': (45, 25), 'saudi': (45, 25),
    'egypt': (30, 27),
    'nigeria': (8, 9),
    'kenya': (37.9, 0.1),
    'thailand': (101, 15),
    'taiwan': (121, 24),
    'hong kong': (114.2, 22.3),
    'finland': (25, 62),
    'poland': (20, 52),
    'czech': (15.5, 50),
    'ukraine': (31, 49),
    'iran': (53, 32),
    'pakistan': (69.3, 30.4),
    'indonesia': (106, -6),
    'malaysia': (109, 2),
    'philippines': (122, 13),
    'vietnam': (106, 16),
    'chile': (-71, -30),
    'colombia': (-74, 4),
    'peru': (-76, -10),

    # US Institutions → United States
    'stanford': (-122.2, 37.4), 'harvard': (-71.1, 42.4), 'mit': (-71.1, 42.4),
    'mayo clinic': (-92.5, 44.0), 'johns hopkins': (-76.6, 39.3),
    'nih': (-77.1, 39.0), 'fda': (-77.1, 38.9), 'cdc': (-84.3, 33.8),
    'md anderson': (-95.4, 29.7), 'sloan kettering': (-73.9, 40.8),
    'ucsf': (-122.5, 37.8), 'ucla': (-118.4, 34.1), 'yale': (-72.9, 41.3),
    'michigan': (-83.7, 42.3), 'duke': (-78.9, 36.0), 'penn ': (-75.2, 40.0),
    'columbia': (-73.9, 40.8), 'cornell': (-76.5, 42.4),
    'northwestern': (-87.7, 42.1), 'vanderbilt': (-86.8, 36.2),
    'baylor': (-97.1, 31.5),

    # European institutions
    'oxford': (-1.3, 51.7), 'cambridge': (0.1, 52.2),
    'imperial college': (-0.2, 51.5), 'king\'s college': (-0.1, 51.5),
    'wellcome': (-0.1, 51.5), 'nhs': (-1.5, 52.0),
    'karolinska': (18.0, 59.4), 'max planck': (11.5, 48.2),
    'charité': (13.4, 52.5),

    # Research keywords implying US or global — distribute to US as primary
    'breakthrough t1d': (-98, 39),
    'astrazeneca': (-0.1, 51.5), 'pfizer': (-73.9, 40.8),
    'moderna': (-71.1, 42.4), 'novartis': (8.2, 47.6),
    'roche': (7.6, 47.5), 'bayer': (7.0, 51.0),
    'merck': (-74.5, 40.8), 'eli lilly': (-86.2, 39.8),
    'bristol': (-2.6, 51.5), 'glaxo': (-0.1, 51.5),
    'sanofi': (2.3, 48.9), 'abbvie': (-87.9, 42.2),
    'janssen': (4.4, 51.2),
}

# Deterministic jitter per title so the same article always lands in the same spot
def _jitter(title: str, scale: float = 3.5):
    h = hash(title) & 0xFFFF
    lng_j = ((h & 0xFF) / 255.0 - 0.5) * scale * 2
    lat_j = ((h >> 8) / 255.0 - 0.5) * scale
    return lng_j, lat_j

# Pool of fallback coordinates — spread around the world for "unknown" articles
FALLBACK_COORDS = [
    (-98, 39), (-98, 40), (-95, 38), (-100, 42),  # US cluster
    (10, 51), (2, 46), (-2, 54), (8.2, 46.8),     # Europe cluster
    (105, 35), (138, 36), (78, 22), (128, 37),     # Asia cluster
    (-51, -14), (134, -25), (-96, 60),              # Rest of world
]

def extract_location(title: str, source_name: str = '') -> tuple:
    """Return (country_label, [lng, lat]) for a news article."""
    combined = f'{title} {source_name}'.lower()

    for keyword, coords in LOCATION_MAP.items():
        if keyword in combined:
            # Return human-readable label
            label = keyword.title().strip()
            # Map institution names back to country names for display
            COUNTRY_LABELS = {
                'stanford': 'USA', 'harvard': 'USA', 'mit': 'USA', 'mayo clinic': 'USA',
                'johns hopkins': 'USA', 'nih': 'USA', 'fda': 'USA', 'cdc': 'USA',
                'md anderson': 'USA', 'sloan kettering': 'USA', 'ucsf': 'USA',
                'ucla': 'USA', 'yale': 'USA', 'michigan': 'USA', 'duke': 'USA',
                'columbia': 'USA', 'cornell': 'USA', 'northwestern': 'USA',
                'vanderbilt': 'USA', 'baylor': 'USA', 'penn ': 'USA',
                'oxford': 'UK', 'cambridge': 'UK', 'imperial college': 'UK',
                "king's college": 'UK', 'wellcome': 'UK', 'nhs': 'UK',
                'karolinska': 'Sweden', 'max planck': 'Germany', 'charité': 'Germany',
                'astrazeneca': 'UK', 'pfizer': 'USA', 'moderna': 'USA',
                'novartis': 'Switzerland', 'roche': 'Switzerland', 'bayer': 'Germany',
                'merck': 'USA', 'eli lilly': 'USA', 'bristol': 'UK', 'glaxo': 'UK',
                'sanofi': 'France', 'abbvie': 'USA', 'janssen': 'Netherlands',
                'breakthrough t1d': 'USA', 'u.s.': 'USA', 'u.s': 'USA',
                'american': 'USA', 'uk ': 'UK', ' uk': 'UK',
            }
            display = COUNTRY_LABELS.get(keyword, label)
            lng_j, lat_j = _jitter(title)
            return display, [coords[0] + lng_j, coords[1] + lat_j]

    return None, None  # not found


def fetch_medical_news(query: str = 'clinical trial breakthrough diabetes cancer immunotherapy', num_results: int = 25) -> list:
    params = {
        'engine': 'google_news',
        'q': query,
        'api_key': SERPAPI_KEY,
        'num': num_results,
    }
    try:
        response = requests.get('https://serpapi.com/search', params=params, timeout=12)
        data = response.json()
        news_items = data.get('news_results', [])
    except Exception as e:
        print(f'SerpAPI fetch error: {e}')
        return []

    results = []
    fallback_idx = 0
    for item in news_items:
        title = item.get('title', '')
        source_name = item.get('source', {}).get('name', '')
        label, coords = extract_location(title, source_name)

        if coords is None:
            # Use a deterministic fallback spread across the world
            fcoords = FALLBACK_COORDS[fallback_idx % len(FALLBACK_COORDS)]
            fallback_idx += 1
            lng_j, lat_j = _jitter(title, scale=2.0)
            coords = [fcoords[0] + lng_j, fcoords[1] + lat_j]
            label = 'Global'

        results.append({
            'title': title,
            'link': item.get('link'),
            'source': source_name,
            'thumbnail': item.get('thumbnail'),
            'date': item.get('date'),
            'iso_date': item.get('iso_date'),
            'location': label,
            'coords': coords,
        })
    return results
