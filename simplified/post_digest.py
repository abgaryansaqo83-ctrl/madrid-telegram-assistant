import datetime
from news import fetch_madrid_news, fetch_cultural_events
from restaurants import fetch_new_restaurants
from jobs import get_last_posted_items, save_posted_item
from aiogram import Bot
import os

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
CHAT_ID = -1001234567890  # Telegram խմբի ID

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
    last_posted = get_last_posted_items()  # Returns set of URLs/headlines already posted
    messages = []

    # 1️⃣ Madrid news
    news_items = fetch_madrid_news()
    for item in news_items:
        key = item["link"]
        if key in last_posted:
            continue
        messages.append(f"📰 [{item['lang'].upper()}] {item['title']}\n{item['link']}")
        save_posted_item(key)
        if len(messages) >= 2:
            break

    # 2️⃣ Cultural events
    events = fetch_cultural_events()
    for event in events:
        key = event["link"]
        if key in last_posted:
            continue
        messages.append(f"🎭 [{event['lang'].upper()}] {event['title']}\n{event['link']}")
        save_posted_item(key)
        if len(messages) >= 5:
            break

    # 3️⃣ Restaurants
    restaurants = fetch_new_restaurants(last_posted_links=last_posted, max_items=2)
    for r in restaurants:
        key = r["link"]
        if key in last_posted:
            continue
        messages.append(f"🍽 [{r['lang'].upper()}] {r['name']} — rating {r['rating']} ({r['reviews']} reviews)\n{r['link']}")
        save_posted_item(key)
        if len(messages) >= 5:
            break

    # 4️⃣ Send digest
    if messages:
        digest_text = "\n\n".join(messages)
        await bot.send_message(CHAT_ID, digest_text)
        print(f"[{datetime.datetime.now()}] Digest posted: {len(messages)} items")
    else:
        print(f"[{datetime.datetime.now()}] No new items to post")
