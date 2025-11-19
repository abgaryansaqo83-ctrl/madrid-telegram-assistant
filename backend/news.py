# backend/news.py

import feedparser
import logging
import os
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# News feed sources
SPAIN_FEEDS = [
    {"url": "https://elpais.com/rss/elpais/internacional.xml", "lang": "es", "name": "El País"},
    {"url": "https://www.rt.com/rss/news/", "lang": "ru", "name": "RT"},
]

MADRID_FEEDS = [
    {"url": "https://elpais.com/rss/ccaa/madrid.xml", "name": "El País Madrid", "lang": "es"},
    {"url": "https://www.20minutos.es/rss/comunidad-de-madrid/", "name": "20 Minutos Madrid", "lang": "es"},
    {"url": "https://www.madrid24horas.com/rss/listado/", "name": "Madrid 24 Horas", "lang": "es"},
]

# Cultural venues (static - no RSS available)
CULTURAL_VENUES = [
    {"title": "🎭 Teatro Real", "link": "https://www.teatro-real.com/es/temporada", "description": "Ópera y ballet"},
    {"title": "🎬 Cine Doré (Filmoteca)", "link": "https://www.culturaydeporte.gob.es/cultura/areas/cine/mc/fe/cine-dore/programacion.html", "description": "Cine clásico 2.5€"},
    {"title": "🎪 Matadero Madrid", "link": "https://www.mataderomadrid.org/programacion", "description": "Arte contemporáneo"},
    {"title": "🎥 Yelmo Cines Ideal", "link": "https://yelmocines.es/cines/madrid/yelmo-cines-ideal", "description": "Cine V.O. centro"},
    {"title": "🎭 Teatros del Canal", "link": "https://www.teatroscanal.com/", "description": "Teatro y danza"},
]

# OpenWeather API (free tier)
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

# Traffic info (static - no free real-time RSS)
TRAFFIC_INFO = {
    "morning_rush": "🚗 Hora punta mañana: 7:30-9:30 (M-30, A-2, A-6 congestionadas)",
    "evening_rush": "🚙 Hora punta tarde: 18:00-20:00 (salidas centro congestionadas)",
    "link": "https://www.tomtom.com/traffic-index/madrid-traffic/",
    "dgt_link": "https://infocar.dgt.es/etraffic/",
}

def fetch_feed_items(feed_list: List[Dict], max_items: int = 5, max_age_days: int = 7) -> List[Dict]:
    """
    Fetch and parse RSS feed items with error handling
    
    Args:
        feed_list: List of feed dictionaries with 'url', 'lang', 'name'
        max_items: Maximum items to fetch per feed
        max_age_days: Maximum age of items in days (default 7)
        
    Returns:
        List of news items with title, link, lang, source, published
    """
    items = []
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    
    for feed in feed_list:
        try:
            logger.info(f"Fetching feed: {feed.get('name', feed['url'])}")
            parsed = feedparser.parse(feed["url"], timeout=10)
            
            # Check if feed was successfully parsed
            if parsed.bozo and parsed.bozo_exception:
                logger.warning(f"Feed parse error for {feed['url']}: {parsed.bozo_exception}")
                continue
            
            if not parsed.entries:
                logger.warning(f"No entries found in feed: {feed['url']}")
                continue
            
            feed_items_count = 0
            for entry in parsed.entries:
                if feed_items_count >= max_items:
                    break
                
                try:
                    # Parse publication date
                    published = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                        except:
                            pass
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        try:
                            published = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                        except:
                            pass
                    
                    # Skip old items if date is available
                    if published and published < cutoff_time:
                        logger.debug(f"Skipping old item: {entry.get('title', 'No title')}")
                        continue
                    
                    # Extract item data
                    item = {
                        "title": entry.get('title', 'No title'),
                        "link": entry.get('link', ''),
                        "lang": feed.get("lang", "es"),
                        "source": feed.get("name", "Unknown"),
                        "published": published.isoformat() if published else None
                    }
                    
                    # Optional: add description/summary if available
                    if hasattr(entry, 'summary'):
                        item["summary"] = entry.summary[:200]  # Limit length
                    
                    items.append(item)
                    feed_items_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing entry from {feed['url']}: {e}")
                    continue
            
            logger.info(f"Fetched {feed_items_count} items from {feed.get('name', feed['url'])}")
            
        except Exception as e:
            logger.error(f"Error fetching feed {feed.get('url', 'unknown')}: {e}")
            continue
    
    return items

def fetch_weather_madrid() -> Optional[Dict]:
    """
    Fetch current weather for Madrid from OpenWeather API
    
    Returns:
        Weather data dictionary or None
    """
    if not OPENWEATHER_API_KEY:
        logger.warning("OpenWeather API key not configured")
        return None
    
    try:
        params = {
            "q": "Madrid,ES",
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "es"
        }
        
        response = requests.get(OPENWEATHER_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        weather = {
            "temp": round(data["main"]["temp"]),
            "feels_like": round(data["main"]["feels_like"]),
            "description": data["weather"][0]["description"].capitalize(),
            "humidity": data["main"]["humidity"],
            "wind_speed": round(data["wind"]["speed"] * 3.6, 1),  # m/s to km/h
        }
        
        logger.info(f"Fetched weather: {weather['temp']}°C, {weather['description']}")
        return weather
        
    except Exception as e:
        logger.error(f"Error fetching weather: {e}")
        return None

def fetch_madrid_news(max_items: int = 5) -> List[Dict]:
    """
    Fetch latest news from Madrid-specific feeds
    
    Args:
        max_items: Maximum items to fetch per feed
        
    Returns:
        List of Madrid news items
    """
    try:
        news = fetch_feed_items(MADRID_FEEDS, max_items=max_items, max_age_days=7)
        logger.info(f"Fetched {len(news)} Madrid news items")
        return news
    except Exception as e:
        logger.error(f"Error fetching Madrid news: {e}")
        return []

def fetch_spain_news(max_items: int = 5) -> List[Dict]:
    """
    Fetch latest news from Spain-wide feeds
    
    Args:
        max_items: Maximum items to fetch per feed
        
    Returns:
        List of Spain news items
    """
    try:
        news = fetch_feed_items(SPAIN_FEEDS, max_items=max_items, max_age_days=7)
        logger.info(f"Fetched {len(news)} Spain news items")
        return news
    except Exception as e:
        logger.error(f"Error fetching Spain news: {e}")
        return []

def get_cultural_venues() -> List[Dict]:
    """
    Get cultural venues info (static list)
    
    Returns:
        List of cultural venue items
    """
    try:
        logger.info(f"Returning {len(CULTURAL_VENUES)} cultural venues")
        return CULTURAL_VENUES.copy()
    except Exception as e:
        logger.error(f"Error getting cultural venues: {e}")
        return []

def get_traffic_info() -> Dict:
    """
    Get traffic information (static info + links)
    
    Returns:
        Traffic info dictionary
    """
    try:
        current_hour = datetime.now().hour
        
        # Determine rush hour status
        if 7 <= current_hour <= 9:
            status = "morning_rush"
        elif 18 <= current_hour <= 20:
            status = "evening_rush"
        else:
            status = "normal"
        
        info = {
            "status": status,
            "message": TRAFFIC_INFO.get(status, "Tráfico normal"),
            "link": TRAFFIC_INFO["link"],
            "dgt_link": TRAFFIC_INFO["dgt_link"]
        }
        
        logger.info(f"Traffic status: {status}")
        return info
        
    except Exception as e:
        logger.error(f"Error getting traffic info: {e}")
        return {"status": "unknown", "message": "Info no disponible"}

def get_all_madrid_info(max_items_per_feed: int = 3) -> Dict[str, any]:
    """
    Fetch all Madrid information in one call
    
    Args:
        max_items_per_feed: Maximum items per feed
        
    Returns:
        Dictionary with 'news', 'weather', 'traffic', 'cultural' keys
    """
    try:
        return {
            "news": fetch_madrid_news(max_items=max_items_per_feed),
            "weather": fetch_weather_madrid(),
            "traffic": get_traffic_info(),
            "cultural": get_cultural_venues()
        }
    except Exception as e:
        logger.error(f"Error fetching all Madrid info: {e}")
        return {"news": [], "weather": None, "traffic": {}, "cultural": []}

def format_news_for_telegram(news_items: List[Dict], max_items: int = 5) -> str:
    """
    Format news items for Telegram message
    
    Args:
        news_items: List of news dictionaries
        max_items: Maximum items to include
        
    Returns:
        Formatted string ready for Telegram
    """
    if not news_items:
        return "📭 No hay noticias disponibles."
    
    formatted = []
    for item in news_items[:max_items]:
        source = item.get('source', 'Unknown')
        title = item.get('title', 'No title')
        link = item.get('link', '')
        
        formatted.append(f"📰 <b>{source}</b>: {title}\n{link}")
    
    return "\n\n".join(formatted)

def format_weather_for_telegram(weather: Optional[Dict]) -> str:
    """
    Format weather data for Telegram message
    
    Args:
        weather: Weather dictionary
        
    Returns:
        Formatted string
    """
    if not weather:
        return "🌤️ Clima no disponible"
    
    return (
        f"🌤️ <b>Clima en Madrid</b>\n"
        f"🌡️ Temperatura: {weather['temp']}°C (sensación {weather['feels_like']}°C)\n"
        f"☁️ {weather['description']}\n"
        f"💨 Viento: {weather['wind_speed']} km/h\n"
        f"💧 Humedad: {weather['humidity']}%"
    )

def format_traffic_for_telegram(traffic: Dict) -> str:
    """
    Format traffic info for Telegram message
    
    Args:
        traffic: Traffic dictionary
        
    Returns:
        Formatted string
    """
    message = traffic.get('message', 'Tráfico normal')
    link = traffic.get('link', '')
    dgt_link = traffic.get('dgt_link', '')
    
    return (
        f"🚦 <b>Tráfico en Madrid</b>\n"
        f"{message}\n\n"
        f"📊 <a href='{link}'>Ver mapa de tráfico</a>\n"
        f"🚨 <a href='{dgt_link}'>Incidencias DGT</a>"
    )

def format_cultural_for_telegram(venues: List[Dict]) -> str:
    """
    Format cultural venues for Telegram message
    
    Args:
        venues: List of venue dictionaries
        
    Returns:
        Formatted string
    """
    if not venues:
        return "🎭 No hay info cultural disponible"
    
    formatted = ["🎭 <b>Cultura y Cine</b>\n"]
    for venue in venues:
        title = venue.get('title', '')
        link = venue.get('link', '')
        desc = venue.get('description', '')
        formatted.append(f"{title}: {desc}\n<a href='{link}'>Ver programación</a>")
    
    return "\n\n".join(formatted)
