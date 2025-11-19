# backend/news.py

import feedparser
import logging
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
    {"url": "https://www.abc.es/rss/atom/espana/madrid", "name": "ABC Madrid", "lang": "es"},
]

# Cultural event sources (static for now, could be made dynamic)
CULTURAL_EVENTS = [
    {"title": "Teatro Real - New Season", "link": "https://www.teatro-real.com/es", "lang": "es"},
    {"title": "Cineteca Madrid - Family Cinema", "link": "https://www.cineteca.es", "lang": "es"},
    {"title": "Matadero Madrid - Art Exhibitions", "link": "https://www.mataderomadrid.org", "lang": "es"},
]

def fetch_feed_items(feed_list: List[Dict], max_items: int = 5, max_age_days: int = 1) -> List[Dict]:
    """
    Fetch and parse RSS feed items with error handling
    
    Args:
        feed_list: List of feed dictionaries with 'url', 'lang', 'name'
        max_items: Maximum items to fetch per feed
        max_age_days: Maximum age of items in days
        
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
                        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        published = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                    
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

def fetch_madrid_news(max_items: int = 5) -> List[Dict]:
    """
    Fetch latest news from Madrid-specific feeds
    
    Args:
        max_items: Maximum items to fetch per feed
        
    Returns:
        List of Madrid news items
    """
    try:
        news = fetch_feed_items(MADRID_FEEDS, max_items=max_items)
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
        news = fetch_feed_items(SPAIN_FEEDS, max_items=max_items)
        logger.info(f"Fetched {len(news)} Spain news items")
        return news
    except Exception as e:
        logger.error(f"Error fetching Spain news: {e}")
        return []

def fetch_cultural_events() -> List[Dict]:
    """
    Fetch cultural events (currently static, could be made dynamic)
    
    Returns:
        List of cultural event items
    """
    try:
        logger.info(f"Returning {len(CULTURAL_EVENTS)} cultural events")
        return CULTURAL_EVENTS.copy()
    except Exception as e:
        logger.error(f"Error fetching cultural events: {e}")
        return []

def get_all_news(max_items_per_feed: int = 3) -> Dict[str, List[Dict]]:
    """
    Fetch all news types in one call
    
    Args:
        max_items_per_feed: Maximum items per feed
        
    Returns:
        Dictionary with 'madrid', 'spain', 'cultural' keys
    """
    try:
        return {
            "madrid": fetch_madrid_news(max_items=max_items_per_feed),
            "spain": fetch_spain_news(max_items=max_items_per_feed),
            "cultural": fetch_cultural_events()
        }
    except Exception as e:
        logger.error(f"Error fetching all news: {e}")
        return {"madrid": [], "spain": [], "cultural": []}

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
        return "No news available at the moment."
    
    formatted = []
    for item in news_items[:max_items]:
        source = item.get('source', 'Unknown')
        lang = item.get('lang', 'es').upper()
        title = item.get('title', 'No title')
        link = item.get('link', '')
        
        formatted.append(f"📰 [{lang}] {source}: {title}\n{link}")
    
    return "\n\n".join(formatted)
