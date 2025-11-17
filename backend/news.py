import requests
import feedparser

NEWS_FEED = "https://www.comunidad.madrid/servicios/rss"

def fetch_madrid_news(limit: int = 3):
    try:
        feed = feedparser.parse(NEWS_FEED)
        items = feed.entries[:limit]
        news_list = []

        for item in items:
            title = item.get("title", "Без названия")
            link = item.get("link", "")
            news_list.append(f"📰 {title}\n🔗 {link}")

        return "\n\n".join(news_list)

    except Exception as e:
        return f"❌ News fetch error: {e}"
