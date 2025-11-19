import datetime
from news import fetch_madrid_news, fetch_cultural_events
#from restaurants import fetch_new_restaurants
from jobs import get_last_posted_items, save_posted_item
from aiogram import Bot
import os

# Stub for restaurants
def fetch_new_restaurants(last_posted_links=None, max_items=2):
    return []

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN missing")

bot = Bot(token=TOKEN)
CHAT_ID = int(os.getenv("CHAT_ID", "-1001234567890"))

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
    last_posted = get_last_posted_items()
    messages = []

    # Madrid news
    for item in fetch_madrid_news():
        key = item["link"]
        if key in last_posted: continue
        messages.append(f"📰 [{item['lang'].upper()}] {item['title']}\n{item['link']}")
        save_posted_item(key)
        if len(messages) >= 2: break

    # Cultural events
    for event in fetch_cultural_events():
        key = event["link"]
        if key in last_posted: continue
        messages.append(f"🎭 [{event['lang'].upper()}] {event['title']}\n{event['link']}")
        save_posted_item(key)
        if len(messages) >= 5: break

    # Restaurants
    for r in fetch_new_restaurants(last_posted_links=last_posted, max_items=2):
        key = r["link"]
        if key in last_posted: continue
        messages.append(f"🍽 [{r['lang'].upper()}] {r['name']} — rating {r['rating']} ({r['reviews']} reviews)\n{r['link']}")
        save_posted_item(key)
        if len(messages) >= 5: break

    if messages:
        digest_text = "\n\n".join(messages)[:4000]
        await bot.send_message(CHAT_ID, digest_text)
        print(f"[{datetime.datetime.now()}] Digest posted: {len(messages)} items")
    else:
        print(f"[{datetime.datetime.now()}] No new items to post")
