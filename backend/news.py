# backend/news.py

import feedparser
import logging
import os
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Madrid News Feeds (6 sources)
MADRID_FEEDS = [
    {"url": "https://www.madrid24horas.com/rss/ultima-hora/", "name": "Madrid 24h", "lang": "es"},
    {"url": "https://www.madridiario.es/feed/", "name": "Madridiario", "lang": "es"},
    {"url": "https://www.eldiariodemadrid.es/rss/madrid/", "name": "El Diario de Madrid", "lang": "es"},
    {"url": "https://diario.madrid.es/feed", "name": "Ayuntamiento Madrid", "lang": "es"},
    {"url": "https://elpais.com/rss/ccaa/madrid.xml", "name": "El País Madrid", "lang": "es"},
    {"url": "https://www.20minutos.es/rss/comunidad-de-madrid/", "name": "20 Minutos Madrid", "lang": "es"},
]

# Spain News Feeds (2 sources)
SPAIN_FEEDS = [
    {"url": "https://elpais.com/rss/elpais/internacional.xml", "lang": "es", "name": "El País España"},
    {"url": "https://www.rt.com/rss/news/", "lang": "ru", "name": "RT Noticias"},
]

# Cultural/Events Feeds (3 sources)
CULTURAL_FEEDS = [
    {"url": "https://www.madrid24horas.com/rss/que-hacer/", "name": "Qué Hacer Madrid", "lang": "es"},
    {"url": "https://www.madrid24horas.com/rss/eventos/", "name": "Eventos Madrid", "lang": "es"},
    {"url": "https://www.eldiariodemadrid.es/rss/planes-por-madrid/", "name": "Planes Madrid", "lang": "es"},
]

# Traffic/Mobility Feed (1 source)
TRAFFIC_FEED = {"url": "https://www.eldiariodemadrid.es/rss/movilidad/", "name": "Movilidad Madrid", "lang": "es"}

# Weather Feed (AEMET - Spanish official meteorology)
WEATHER_FEED = {"url": "https://www.aemet.es/es/rss_info/avisos/mad", "name": "AEMET Madrid", "lang": "es"}

# Traffic links (for reference)
TRAFFIC_LINKS = {
    "informo": "https://informo.madrid.es/",
    "dgt": "https://infocar.dgt.es/etraffic/",
    "cameras": "https://www.race.es/mapa-de-carreteras-espana/camaras-trafico-madrid",
}

def get_weather_madrid():
    """
    Get real weather data for Madrid using OpenWeatherMap API
    Returns: dict with temp, feels_like, description, icon
    """
    try:
        # OpenWeatherMap Free API
        API_KEY = os.getenv("OPENWEATHER_API_KEY")
        
        if not API_KEY:
            # Fallback to placeholder if no API key
            logger.warning("No OpenWeatherMap API key found, using placeholder data")
            return {
                "temp": 12,
                "feels_like": 10,
                "description": "облачно",
                "icon": "☁️"
            }
        
        url = f"https://api.openweathermap.org/data/2.5/weather?q=Madrid,ES&appid={API_KEY}&units=metric&lang=ru"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Map weather icons
        weather_icons = {
            "Clear": "☀️",
            "Clouds": "☁️",
            "Rain": "🌧️",
            "Drizzle": "🌦️",
            "Thunderstorm": "⛈️",
            "Snow": "❄️",
            "Mist": "🌫️",
            "Fog": "🌫️"
        }
        
        main_weather = data["weather"][0]["main"]
        icon = weather_icons.get(main_weather, "🌤️")
        
        return {
            "temp": round(data["main"]["temp"]),
            "feels_like": round(data["main"]["feels_like"]),
            "description": data["weather"][0]["description"],
            "icon": icon
        }
        
    except Exception as e:
        logger.error(f"Error fetching weather: {e}")
        # Fallback data
        return {
            "temp": 12,
            "feels_like": 10,
            "description": "данные недоступны",
            "icon": "🌤️"
        }

def fetch_feed_items(feed_list: List[Dict], max_items: int = 3, max_age_days: int = 7) -> List[Dict]:
    """
    Fetch and parse RSS feed items with error handling
    
    Args:
        feed_list: List of feed dictionaries with 'url', 'lang', 'name'
        max_items: Maximum items to fetch per feed (1-3)
        max_age_days: Maximum age of items in days (default 7)
        
    Returns:
        List of news items with title, link, lang, source, published
    """
    items = []
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    
    for feed in feed_list:
        try:
            logger.info(f"Fetching feed: {feed.get('name', feed['url'])}")
            parsed = feedparser.parse(feed["url"])
            
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
                        "title": entry.get('title', 'Sin título'),
                        "link": entry.get('link', ''),
                        "lang": feed.get("lang", "es"),
                        "source": feed.get("name", "Desconocido"),
                        "published": published.isoformat() if published else None
                    }
                    
                    # Optional: add description/summary if available
                    if hasattr(entry, 'summary'):
                        item["summary"] = entry.summary[:150]
                    
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

def fetch_madrid_news(max_items: int = 3) -> List[Dict]:
    """
    Fetch latest Madrid news (1-3 items)
    
    Returns:
        List of 1-3 Madrid news items
    """
    try:
        news = fetch_feed_items(MADRID_FEEDS, max_items=1, max_age_days=7)
        logger.info(f"Fetched {len(news)} Madrid news items")
        return news[:max_items]
    except Exception as e:
        logger.error(f"Error fetching Madrid news: {e}")
        return []

def fetch_spain_news(max_items: int = 3) -> List[Dict]:
    """
    Fetch latest Spain news (1-3 items)
    
    Returns:
        List of 1-3 Spain news items
    """
    try:
        news = fetch_feed_items(SPAIN_FEEDS, max_items=1, max_age_days=7)
        logger.info(f"Fetched {len(news)} Spain news items")
        return news[:max_items]
    except Exception as e:
        logger.error(f"Error fetching Spain news: {e}")
        return []

def fetch_cultural_news(max_items: int = 3) -> List[Dict]:
    """
    Fetch latest cultural/events news (1-3 items)
    
    Returns:
        List of 1-3 cultural items
    """
    try:
        news = fetch_feed_items(CULTURAL_FEEDS, max_items=1, max_age_days=7)
        logger.info(f"Fetched {len(news)} cultural items")
        return news[:max_items]
    except Exception as e:
        logger.error(f"Error fetching cultural news: {e}")
        return []

def fetch_traffic_news(max_items: int = 3) -> List[Dict]:
    """
    Fetch latest traffic/mobility news (1-3 items)
    
    Returns:
        List of 1-3 traffic items
    """
    try:
        news = fetch_feed_items([TRAFFIC_FEED], max_items=max_items, max_age_days=2)
        logger.info(f"Fetched {len(news)} traffic items")
        return news[:max_items]
    except Exception as e:
        logger.error(f"Error fetching traffic news: {e}")
        return []

def fetch_weather_alerts() -> List[Dict]:
    """
    Fetch weather alerts from AEMET
    
    Returns:
        List of weather alerts (if any)
    """
    try:
        alerts = fetch_feed_items([WEATHER_FEED], max_items=3, max_age_days=1)
        logger.info(f"Fetched {len(alerts)} weather alerts")
        return alerts
    except Exception as e:
        logger.error(f"Error fetching weather alerts: {e}")
        return []

def format_news_section(items: List[Dict], title: str, emoji: str) -> str:
    """
    Format a news section for Telegram
    
    Args:
        items: List of news items
        title: Section title
        emoji: Section emoji
        
    Returns:
        Formatted string or empty if no items
    """
    if not items:
        return ""
    
    lines = [f"{emoji} <b>{title}</b>\n"]
    for item in items[:3]:
        source = item.get('source', 'Fuente')
        title_text = item.get('title', 'Sin título')
        link = item.get('link', '')
        
        lines.append(f"• <b>{source}</b>: {title_text}")
        if link:
            lines.append(f"  {link}")
    
    return "\n".join(lines)

def format_manual_news() -> str:
    """
    Format all news for /news command
    - Madrid news (1-3)
    - Spain news (1-3)
    - Cultural (1-3)
    
    Returns:
        Formatted news string in original languages
    """
    try:
        sections = []
        
        # Madrid news
        madrid_news = fetch_madrid_news(max_items=3)
        madrid_section = format_news_section(madrid_news, "Noticias de Madrid", "🏛️")
        if madrid_section:
            sections.append(madrid_section)
        
        # Spain news
        spain_news = fetch_spain_news(max_items=3)
        spain_section = format_news_section(spain_news, "Noticias de España", "📰")
        if spain_section:
            sections.append(spain_section)
        
        # Cultural
        cultural = fetch_cultural_news(max_items=3)
        cultural_section = format_news_section(cultural, "Cultura y Eventos", "🎭")
        if cultural_section:
            sections.append(cultural_section)
        
        if not sections:
            return "📭 Нет доступных новостей."
        
        return "\n\n".join(sections)
        
    except Exception as e:
        logger.error(f"Error formatting news: {e}")
        return "❌ Ошибка при получении новостей."

def format_morning_news() -> str:
    """
    Format morning news for 8:30 AM auto-post
    - Real weather data (OpenWeatherMap API)
    - Traffic (casual style)
    Russian language with Spanish humor
    
    Returns:
        Formatted morning news string in Russian
    """
    try:
        # Get real weather
        weather = get_weather_madrid()
        traffic_news = fetch_traffic_news(max_items=2)
        
        # Morning message
        lines = ["☀️ <b>Доброе утро, Мадрид!</b> 🇪🇸\n"]
        
        # Weather with real data
        lines.append("🌤️ <b>ПОГОДА НА СЕГОДНЯ:</b>")
        lines.append(f"{weather['icon']} {weather['description'].capitalize()}")
        lines.append(f"Температура: {weather['temp']}°C")
        lines.append(f"Ощущается: {weather['feels_like']}°C")
        
        # Funny advice based on temperature
        if weather['feels_like'] < 10:
            lines.append("🥶 Совет: одевайтесь слоями!")
            lines.append("(Даже испанцы уже в пальто 😄)")
        elif weather['feels_like'] > 25:
            lines.append("🔥 Совет: прячьтесь в тень!")
            lines.append("(Испанцы уже на сиесте 😴)")
        else:
            lines.append("👌 Совет: идеальная погода!")
            lines.append("(Даже без куртки можно 😊)")
        
        lines.append("")
        
        # Traffic situation
        lines.append("🚗 <b>СИТУАЦИЯ НА ДОРОГАХ:</b>")
        
        if traffic_news:
            for item in traffic_news[:2]:
                title = item.get('title', 'Información de tráfico')
                lines.append(f"• {title}")
        else:
            lines.append("• M-30 → как всегда пробка 🚙")
            lines.append("• A-2 → порядок ✅")
            lines.append("• Gran Vía → туристы everywhere 👥")
        
        lines.append("💡 Совет: метро быстрее! 🚇\n")
        
        # Close
        lines.append("☕ <b>Хорошего дня, мадридцы!</b>")
        lines.append(f"🔗 <a href='{TRAFFIC_LINKS['dgt']}'>Полная информация о движении</a>")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Error formatting morning news: {e}")
        return "☀️ Доброе утро, Мадрид! 🇪🇸\n☕ Хорошего дня!"
