# simplified/post_digest.py

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from dotenv import load_dotenv

# Import from backend module (not relative imports for simplified)
from backend.news import fetch_madrid_news, fetch_cultural_news
from backend.jobs import get_last_posted_items, save_posted_item

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN missing in environment variables")

CHAT_ID = os.getenv("CHAT_ID")
if not CHAT_ID:
    raise ValueError("CHAT_ID missing in environment variables")

try:
    CHAT_ID = int(CHAT_ID)
except ValueError:
    raise ValueError(f"CHAT_ID must be a valid integer, got: {CHAT_ID}")

# Initialize bot
bot = Bot(token=TOKEN)

# Digest configuration
MAX_MESSAGE_LENGTH = 4000
MAX_ITEMS_PER_DIGEST = 10
MAX_NEWS_ITEMS = 3
MAX_CULTURAL_ITEMS = 2
MAX_RESTAURANT_ITEMS = 2

def fetch_new_restaurants(last_posted_links: set = None, max_items: int = 2) -> List[Dict]:
    logger.debug("Restaurant fetching not yet implemented")
    return []

def restaurant_score(restaurant: Dict) -> int:
    score = 0
    rating = restaurant.get("rating", 0)
    if rating >= 4.5:
        score += 3
    elif rating >= 4.2:
        score += 2
    elif rating >= 4.0:
        score += 1
    reviews = restaurant.get("reviews", 0)
    if reviews >= 100:
        score += 3
    elif reviews >= 50:
        score += 2
    elif reviews >= 30:
        score += 1
    return score

async def post_digest() -> None:
    try:
        last_posted = get_last_posted_items()
        messages = []

        # Fetch Madrid news
        logger.info("Fetching Madrid news...")
        try:
            news_items = fetch_madrid_news(max_items=MAX_NEWS_ITEMS)
            for item in news_items:
                key = item.get("link")
                if not key or key in last_posted:
                    continue
                lang = item.get('lang', 'es').upper()
                source = item.get('source', 'Unknown')
                title = item.get('title', 'No title')
                messages.append(f"📰 [{lang}] {source}: {title}\n{key}")
                save_posted_item(key)
                if len(messages) >= MAX_ITEMS_PER_DIGEST:
                    break
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
        
        # Fetch cultural events
        if len(messages) < MAX_ITEMS_PER_DIGEST:
            logger.info("Fetching cultural events...")
            try:
                events = fetch_cultural_news(max_items=MAX_CULTURAL_ITEMS)
                for event in events:
                    key = event.get("link")
                    if not key or key in last_posted:
                        continue
                    lang = event.get('lang', 'es').upper()
                    title = event.get('title', 'No title')
                    messages.append(f"🎭 [{lang}] {title}\n{key}")
                    save_posted_item(key)
                    if len(messages) >= MAX_ITEMS_PER_DIGEST:
                        break
            except Exception as e:
                logger.error(f"Error fetching cultural events: {e}")
        
        # Fetch restaurants (when implemented)
        if len(messages) < MAX_ITEMS_PER_DIGEST:
            logger.info("Checking for restaurants...")
            try:
                restaurants = fetch_new_restaurants(
                    last_posted_links=last_posted,
                    max_items=MAX_RESTAURANT_ITEMS
                )
                restaurants_sorted = sorted(
                    restaurants,
                    key=restaurant_score,
                    reverse=True
                )
                for restaurant in restaurants_sorted:
                    key = restaurant.get("link")
                    if not key or key in last_posted:
                        continue
                    lang = restaurant.get('lang', 'es').upper()
                    name = restaurant.get('name', 'Unknown')
                    rating = restaurant.get('rating', 'N/A')
                    reviews = restaurant.get('reviews', 0)
                    messages.append(
                        f"🍽 [{lang}] {name} — ⭐ {rating} ({reviews} reviews)\n{key}"
                    )
                    save_posted_item(key)
                    if len(messages) >= MAX_ITEMS_PER_DIGEST:
                        break
            except Exception as e:
                logger.error(f"Error fetching restaurants: {e}")

        # Send digest if there are new items
        if messages:
            digest_text = "\n\n".join(messages)
            if len(digest_text) > MAX_MESSAGE_LENGTH:
                digest_text = digest_text[:MAX_MESSAGE_LENGTH - 50] + "\n\n... (truncated)"
            header = f"📬 **Madrid Digest** - {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            digest_text = header + digest_text
            try:
                await bot.send_message(
                    CHAT_ID,
                    digest_text,
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
                logger.info(f"✅ Digest posted: {len(messages)} items")
            except TelegramAPIError as e:
                logger.error(f"Telegram API error: {e}")
                try:
                    await bot.send_message(
                        CHAT_ID,
                        digest_text.replace("**", ""),
                        disable_web_page_preview=True
                    )
                    logger.info(f"✅ Digest posted (plain text): {len(messages)} items")
                except Exception as e2:
                    logger.error(f"Failed to send digest: {e2}")
        else:
            logger.info("ℹ️ No new items to post")
    except Exception as e:
        logger.error(f"Critical error in post_digest: {e}", exc_info=True)
        raise

async def close_bot():
    try:
        await bot.session.close()
        logger.info("Bot session closed")
    except Exception as e:
        logger.error(f"Error closing bot session: {e}")
