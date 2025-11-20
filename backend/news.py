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
        return news[:max_items]  # Limit to max 3 total
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
        return news[:max_items]  # Limit to max 3 total
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
        return news[:max_items]  # Limit to max 3 total
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
        return news[:max_items]  # Limit to max 3 total
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

def get_all_madrid_info() -> Dict[str, any]:
    """
    Fetch all Madrid information in one call
    
    Returns:
        Dictionary with 'madrid_news', 'spain_news', 'cultural', 'traffic', 'weather'
    """
    try:
        return {
            "madrid_news": fetch_madrid_news(max_items=3),
            "spain_news": fetch_spain_news(max_items=3),
            "cultural": fetch_cultural_news(max_items=3),
            "traffic": fetch_traffic_news(max_items=3),
            "weather": fetch_weather_alerts(),
        }
    except Exception as e:
        logger.error(f"Error fetching all Madrid info: {e}")
        return {
            "madrid_news": [],
            "spain_news": [],
            "cultural": [],
            "traffic": [],
            "weather": []
        }

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
    for item in items[:3]:  # Max 3 items
        source = item.get('source', 'Fuente')
        title_text = item.get('title', 'Sin título')
        link = item.get('link', '')
        
        lines.append(f"• <b>{source}</b>: {title_text}")
        if link:
            lines.append(f"  {link}")
    
    return "\n".join(lines)

def format_all_news_for_telegram() -> str:
    """
    Fetch and format all news for Telegram /news command
    
    Returns:
        Complete formatted news message
    """
    try:
        info = get_all_madrid_info()
        
        sections = []
        
        # Madrid news (1-3 items)
        madrid_section = format_news_section(
            info['madrid_news'],
            "Noticias de Madrid",
            "🏛️"
        )
        if madrid_section:
            sections.append(madrid_section)
        
        # Spain news (1-3 items)
        spain_section = format_news_section(
            info['spain_news'],
            "Noticias de España",
            "📰"
        )
        if spain_section:
            sections.append(spain_section)
        
        # Cultural (1-3 items)
        cultural_section = format_news_section(
            info['cultural'],
            "Cultura y Eventos",
            "🎭"
        )
        if cultural_section:
            sections.append(cultural_section)
        
        # Traffic (1-3 items)
        traffic_section = format_news_section(
            info['traffic'],
            "Tráfico y Movilidad",
            "🚦"
        )
        if traffic_section:
            sections.append(traffic_section)
        
        # Weather alerts
        if info['weather']:
            weather_lines = ["🌤️ <b>Alertas Meteorológicas</b>\n"]
            for alert in info['weather'][:2]:  # Max 2 alerts
                title = alert.get('title', 'Alerta')
                weather_lines.append(f"⚠️ {title}")
            sections.append("\n".join(weather_lines))
        
        # Traffic links
        sections.append(
            f"🔗 <b>Más información</b>\n"
            f"📊 <a href='{TRAFFIC_LINKS['informo']}'>Tráfico Madrid (Informo)</a>\n"
            f"🚨 <a href='{TRAFFIC_LINKS['dgt']}'>Incidencias DGT</a>"
        )
        
        if not sections:
            return "📭 No hay noticias disponibles en este momento."
        
        return "\n\n".join(sections)
        
    except Exception as e:
        logger.error(f"Error formatting news: {e}")
        return "❌ Error al obtener noticias. Inténtalo más tarde."
