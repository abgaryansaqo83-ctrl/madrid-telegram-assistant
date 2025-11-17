import datetime
from jobs import get_last_posted_items, save_posted_item
from news import fetch_madrid_news, fetch_cultural_events, fetch_new_restaurants
from aiogram import Bot

bot = Bot(token="YOUR_BOT_TOKEN")  # կամ os.getenv("BOT_TOKEN")
CHAT_ID = -1001234567890  # Քո Telegram խմբի ID

# Simple scoring function for restaurants
def restaurant_score(restaurant):
    score = 0
    if restaurant.get("rating", 0) >= 4.2:
        score += 2
    elif restaurant.get("rating", 0) >= 4.0:
        score += 1
    if restaurant.get("reviews", 0) >= 30:
        score += 1
    return score

async def post_digest():
    """
    Post Madrid digest dynamically, only new & relevant items,
    respecting language integrity (no auto translation)
    """

    last_posted = get_last_posted_items()  # Returns a set of URLs/headlines already posted
    messages = []

    # 1️⃣ Fetch Spain / Madrid news
    news_items = fetch_madrid_news()  # List of dicts: {"title": ..., "link": ..., "lang": "ru/es/en"}
    for item in news_items:
        key = item["link"]
        if key in last_posted:
            continue
        messages.append(f"📰 [{item['lang'].upper()}] {item['title']}\n{item['link']}")
        save_posted_item(key)  # Mark as posted
        if len(messages) >= 2:  # max 2 news items
            break

    # 2️⃣ Fetch cultural events / cinema / theatre / kids
    events = fetch_cultural_events()  # List of dicts: {"title":..., "link":..., "lang":...}
    for event in events:
        key = event["link"]
        if key in last_posted:
            continue
        messages.append(f"🎭 [{event['lang'].upper()}] {event['title']}\n{event['link']}")
        save_posted_item(key)
        if len(messages) >= 5:  # max total items = 5
            break

    # 3️⃣ Fetch new restaurants (only if score >= Medium)
    restaurants = fetch_new_restaurants()  # List of dicts: {"name":..., "link":..., "rating":..., "reviews":..., "lang":...}
    for r in restaurants:
        if restaurant_score(r) < 2:
            continue
        key = r["link"]
        if key in last_posted:
            continue
        messages.append(f"🍽 [{r['lang'].upper()}] {r['name']} — rating {r['rating']} ({r['reviews']} reviews)\n{r['link']}")
        save_posted_item(key)
        if len(messages) >= 5:
            break

    # 4️⃣ Send digest if we have at least 1 new item
    if messages:
        digest_text = "\n\n".join(messages)
        await bot.send_message(CHAT_ID, digest_text)
        print(f"[{datetime.datetime.now()}] Digest posted: {len(messages)} items")
    else:
        print(f"[{datetime.datetime.now()}] No new items to post")
