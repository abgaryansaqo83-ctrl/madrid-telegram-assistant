# backend/bot.py

import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import F
from dotenv import load_dotenv

from backend.languages import LANG, detect_lang
from backend.jobs import add_offer, add_request, find_matches
from backend.news import fetch_madrid_news

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN missing in environment variables")

bot = Bot(TOKEN)
dp = Dispatcher()

# /start
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    try:
        lang = detect_lang(message.from_user.language_code)
        await message.answer(LANG[lang]["start"])
        logger.info(f"User {message.from_user.id} started bot")
    except Exception as e:
        logger.error(f"Error in start_cmd: {e}")
        await message.answer("Error processing command")

# /news
@dp.message(Command("news"))
async def news_cmd(message: types.Message):
    try:
        lang = detect_lang(message.from_user.language_code)
        news_items = fetch_madrid_news()
        
        if not news_items:
            await message.answer(LANG[lang].get("no_news", "No news available"))
            return
        
        # Format news items
        news_text = ""
        for item in news_items[:5]:  # Limit to 5 items
            news_text += f"📰 {item['title']}\n{item['link']}\n\n"
        
        await message.answer(f"{LANG[lang]['news']}\n\n{news_text}")
        logger.info(f"User {message.from_user.id} requested news")
    except Exception as e:
        logger.error(f"Error in news_cmd: {e}")
        await message.answer("Error fetching news")

# /offer
@dp.message(F.text.startswith("/offer "))
async def offer_cmd(message: types.Message):
    try:
        lang = detect_lang(message.from_user.language_code)
        text = message.text.replace("/offer ", "").strip()
        
        if not text:
            await message.answer(LANG[lang].get("empty_offer", "Please provide offer details"))
            return
        
        add_offer(message.from_user.id, text)
        await message.answer(LANG[lang]["offer_saved"])
        logger.info(f"User {message.from_user.id} added offer: {text[:50]}")
    except Exception as e:
        logger.error(f"Error in offer_cmd: {e}")
        await message.answer("Error saving offer")

# /request
@dp.message(F.text.startswith("/request "))
async def request_cmd(message: types.Message):
    try:
        lang = detect_lang(message.from_user.language_code)
        text = message.text.replace("/request ", "").strip()
        
        if not text:
            await message.answer(LANG[lang].get("empty_request", "Please provide request details"))
            return
        
        add_request(message.from_user.id, text)
        await message.answer(LANG[lang]["request_saved"])
        logger.info(f"User {message.from_user.id} added request: {text[:50]}")
    except Exception as e:
        logger.error(f"Error in request_cmd: {e}")
        await message.answer("Error saving request")

# /match
@dp.message(Command("match"))
async def match_cmd(message: types.Message):
    try:
        lang = detect_lang(message.from_user.language_code)
        matches = find_matches()

        if not matches:
            await message.answer(LANG[lang]["no_matches"])
            return

        msg = LANG[lang]["matches"] + "\n\n"
        for req, off in matches:
            msg += f"👤 Request: {req['text']}\n💼 Offer: {off['text']}\n---\n"

        await message.answer(msg)
        logger.info(f"User {message.from_user.id} checked matches: {len(matches)} found")
    except Exception as e:
        logger.error(f"Error in match_cmd: {e}")
        await message.answer("Error finding matches")

# /help command
@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    try:
        lang = detect_lang(message.from_user.language_code)
        help_text = """
🤖 Available commands:
/start - Start bot
/news - Get Madrid news
/offer [text] - Post job offer
/request [text] - Post job request
/match - Find job matches
/help - Show this help
        """
        await message.answer(help_text)
    except Exception as e:
        logger.error(f"Error in help_cmd: {e}")

# fallback
@dp.message(F.text)
async def echo(message: types.Message):
    await message.answer("Քեզ լսում եմ, Սաքո։")

async def main():
    try:
        logger.info("Starting bot...")
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Critical error in main: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
