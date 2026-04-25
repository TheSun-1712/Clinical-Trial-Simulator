import os
import json
import requests
from typing import List, Dict

# In a real deployment, store the key securely e.g., in environment variables.
SERPAPI_KEY = os.getenv('SERPAPI_KEY', '15ac2b2f9cc36da18e44a78b028cf924ca8c64f08a7c37772ae7dde184ca73d9')

def fetch_medical_news(query: str = "clinical trial breakthrough diabetes cancer", num_results: int = 20) -> List[Dict]:
    """Fetch recent medical news using SerpAPI Google News engine.
    Returns a list of dicts containing title, link, source, thumbnail, and a naive location extraction.
    """
    params = {
        "engine": "google_news",
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": num_results,
    }
    try:
        response = requests.get("https://serpapi.com/search", params=params, timeout=10)
        data = response.json()
        news_items = data.get("news_results", [])
        # Simple location extraction: look for country names in title using a small list.
        locations = []
        countries = [
            "United States", "USA", "Canada", "Germany", "France", "UK", "United Kingdom",
            "Australia", "China", "India", "Japan", "Brazil", "Mexico", "South Korea",
            "Russia", "Sweden", "Norway", "Denmark", "Netherlands",
        ]
        for item in news_items:
            title = item.get("title", "")
            loc = None
            for c in countries:
                if c.lower() in title.lower():
                    loc = c
                    break
            # Fallback to "World"
            if not loc:
                loc = "World"
            locations.append({
                "title": title,
                "link": item.get("link"),
                "source": item.get("source", {}).get("name"),
                "thumbnail": item.get("thumbnail"),
                "date": item.get("date"),
                "iso_date": item.get("iso_date"),
                "location": loc,
            })
        return locations
    except Exception as e:
        print(f"SerpAPI fetch error: {e}")
        return []
