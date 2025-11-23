import feedparser
import logging
import os
import requests
import random
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
    try:
        API_KEY = os.getenv("OPENWEATHER_API_KEY")
        if not API_KEY:
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
        return {
            "temp": 12,
            "feels_like": 10,
            "description": "данные недоступны",
            "icon": "🌤️"
        }

def fetch_feed_items(feed_list: List[Dict], max_items: int = 3, max_age_days: int = 7) -> List[Dict]:
    items = []
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    for feed in feed_list:
        try:
            logger.info(f"Fetching feed: {feed.get('name', feed['url'])}")
            parsed = feedparser.parse(feed["url"])
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
                    if published and published < cutoff_time:
                        logger.debug(f"Skipping old item: {entry.get('title', 'No title')}")
                        continue
                    item = {
                        "title": entry.get('title', 'Sin título'),
                        "link": entry.get('link', ''),
                        "lang": feed.get("lang", "es"),
                        "source": feed.get("name", "Desconocido"),
                        "published": published.isoformat() if published else None
                    }
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
    try:
        news = fetch_feed_items(MADRID_FEEDS, max_items=1, max_age_days=7)
        logger.info(f"Fetched {len(news)} Madrid news items")
        return news[:max_items]
    except Exception as e:
        logger.error(f"Error fetching Madrid news: {e}")
        return []

def fetch_spain_news(max_items: int = 3) -> List[Dict]:
    try:
        news = fetch_feed_items(SPAIN_FEEDS, max_items=1, max_age_days=7)
        logger.info(f"Fetched {len(news)} Spain news items")
        return news[:max_items]
    except Exception as e:
        logger.error(f"Error fetching Spain news: {e}")
        return []

def fetch_cultural_news(max_items: int = 3) -> List[Dict]:
    try:
        news = fetch_feed_items(CULTURAL_FEEDS, max_items=1, max_age_days=7)
        logger.info(f"Fetched {len(news)} cultural items")
        return news[:max_items]
    except Exception as e:
        logger.error(f"Error fetching cultural news: {e}")
        return []

def fetch_traffic_news(max_items: int = 3) -> List[Dict]:
    try:
        news = fetch_feed_items([TRAFFIC_FEED], max_items=max_items, max_age_days=2)
        logger.info(f"Fetched {len(news)} traffic items")
        return news[:max_items]
    except Exception as e:
        logger.error(f"Error fetching traffic news: {e}")
        return []

def fetch_weather_alerts() -> List[Dict]:
    try:
        alerts = fetch_feed_items([WEATHER_FEED], max_items=3, max_age_days=1)
        logger.info(f"Fetched {len(alerts)} weather alerts")
        return alerts
    except Exception as e:
        logger.error(f"Error fetching weather alerts: {e}")
        return []

def format_news_section(items: List[Dict], title: str, emoji: str) -> str:
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
    try:
        sections = []
        madrid_news = fetch_madrid_news(max_items=3)
        madrid_section = format_news_section(madrid_news, "Noticias de Madrid", "🏛️")
        if madrid_section:
            sections.append(madrid_section)
        spain_news = fetch_spain_news(max_items=3)
        spain_section = format_news_section(spain_news, "Noticias de España", "📰")
        if spain_section:
            sections.append(spain_section)
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
    Формирует утреннее сообщение с погодой, дорожной ситуацией (Google Maps Directions),
    культурными событиями и пожеланием для группы.
    """
    try:
        from backend.ai.traffic import madrid_morning_traffic

        weather = get_weather_madrid()
        greetings = [
            "☀️ Доброе утро, Мадрид! 🇪🇸",
            "😎 Buenos días, Madrid!",
            "🤗 Привет, мадридцы!",
            "🌞 Новый день в Мадриде — начался!",
            "👋 Утро в столице Испании: улыбнитесь!"
        ]
        advices = [
            "Сегодня лучше не спорить с таксистом 😉",
            "Кофе спасает даже от утренних пробок!",
            "Пальто пригодится — но шлепки тоже не забудьте!",
            "Ищите место для суши? Сегодня всё получится!",
            "Зарядка на площади де Кастилья — must have!",
            "Проверьте, закрыта ли ваша линия метро!"
        ]
        wish = random.choice([
            "Улыбнитесь незнакомцу — это испанской традицией считается!",
            "Пусть очередь за чуррос пройдёт быстро!",
            "Сегодня погода для идеального фото в парке!",
            "Пусть утро будет таким же приятным, как свежий круассан!"
        ])
        lines = [random.choice(greetings) + "\n"]
        lines.append("🌤️ <b>ПОГОДА НА СЕГОДНЯ:</b>")
        lines.append(f"{weather['icon']} {weather['description'].capitalize()}")
        lines.append(f"Температура: {weather['temp']}°C")
        lines.append(f"Ощущается: {weather['feels_like']}°C")
        if weather['feels_like'] < 10:
            lines.append("🥶 Совет дня: берегите уши, в Мадриде становится прохладно 😄")
        elif weather['feels_like'] > 25:
            lines.append("🔥 Совет дня: не забудьте бутылку воды и панаму!")
        else:
            lines.append("👌 Совет дня: отличная погода для знакомств!")
        lines.append("")
        lines.append("🚗 <b>СИТУАЦИЯ НА ДОРОГАХ:</b>")
        gmaps_traffic = madrid_morning_traffic()
        lines.append(gmaps_traffic)
        lines.append(random.choice(advices))
        cultural = fetch_cultural_news(max_items=3)
        if cultural:
            lines.append("\n🎭 <b>События и мероприятия:</b>")
            for item in cultural:
                lines.append(f"• {item.get('title', '')}")
                if "link" in item and item["link"]:
                    lines.append(f"  <a href='{item['link']}'>Подробнее</a>")
        lines.append(f"\n☕ <b>Хорошего дня, мадридцы!</b>")
        lines.append(f"😄 {wish}")
        lines.append(f"🔗 <a href='{TRAFFIC_LINKS['dgt']}'>Вся информация о движении</a>")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error formatting morning news: {e}")
        return "☀️ Доброе утро, Мадрид! 🇪🇸\n☕ Хорошего дня!"
