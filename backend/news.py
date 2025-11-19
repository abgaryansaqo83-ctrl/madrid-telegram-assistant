import feedparser
from datetime import datetime, timezone, timedelta

SPAIN_FEEDS = [
    {"url": "https://elpais.com/rss/elpais/internacional.xml", "lang": "es"},
    {"url": "https://www.rt.com/rss/news/", "lang": "ru"},
]

MADRID_FEEDS = [
    {"url": "https://www.madrid.es/portales/munimadrid/es/Inicio/Actualidad/rss", "lang": "es"},
]

def fetch_feed_items(feed_list, max_items=5):
    items = []
    for feed in feed_list:
        try:
            parsed = feedparser.parse(feed["url"])
            for entry in parsed.entries[:max_items]:
                # Check published date (last 24h)
                try:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) - published > timedelta(days=1):
                        continue
                except Exception:
                    pass

                items.append({
                    "title": entry.title,
                    "link": entry.link,
                    "lang": feed["lang"]
                })
        except Exception as e:
            print(f"Error fetching {feed['url']}: {e}")
    return items

def fetch_madrid_news():
    """Return list of recent Madrid news"""
    return fetch_feed_items(MADRID_FEEDS, max_items=2)

def fetch_spain_news():
    """Return list of recent Spain-wide news"""
    return fetch_feed_items(SPAIN_FEEDS, max_items=2)

def fetch_cultural_events():
    """Return sample cultural / theatre / cinema events"""
    return [
        {"title": "New play at Teatro Real", "link": "https://www.teatro-real.com/es", "lang": "es"},
        {"title": "Children's cinema event", "link": "https://www.cineteca.es", "lang": "es"},
    ]
