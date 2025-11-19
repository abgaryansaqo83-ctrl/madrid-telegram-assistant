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
from backend.database import init_db
from backend.memory import save_message_with_analysis

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
# Add import at top
from backend.matching import (
    parse_housing_offer, 
    find_matching_requests,
    find_matching_offers,
    is_housing_offer,
    is_housing_request
)

# Update echo function
@dp.message(F.text)
async def handle_message(message: types.Message):
    # Save conversation to memory
    try:
        keywords = save_message_with_analysis(message.from_user.id, message.text)
        
        # Check if housing-related
        if keywords.get('housing'):
            # Determine if offer or request
            if is_housing_offer(message.text):
                logger.info(f"Housing offer detected: {message.text[:50]}")
                offer_data = parse_housing_offer(message.text)
                
                # Find matching requests
                matches = find_matching_requests(offer_data)
                
                if matches:
                    # Reply to group
                    match_count = len(matches)
                    await message.reply(
                        f"🏠 **{match_count} пользователей** ищут похожее жильё!\n\n"
                        f"Администратор свяжет вас с заинтересованными.",
                        parse_mode="HTML"
                    )
                    logger.info(f"Replied with {match_count} matches")
            
            elif is_housing_request(message.text):
                logger.info(f"Housing request detected: {message.text[:50]}")
                request_data = parse_housing_offer(message.text)
                
                # Find matching offers
                matches = find_matching_offers(request_data)
                
                if matches:
                    # Reply to group
                    match_count = len(matches)
                    await message.reply(
                        f"🏠 **{match_count} предложений** по вашим параметрам найдено!\n\n"
                        f"Администратор свяжет вас с владельцами.",
                        parse_mode="HTML"
                    )
                    logger.info(f"Replied with {match_count} matches")
    
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
    
    # Still show admin contact
    lang = detect_lang(message.from_user.language_code)
    await message.answer(LANG[lang]["contact_admin"])

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
        await message.answer(LANG[lang]["help"])
        logger.info(f"User {message.from_user.id} requested help")
    except Exception as e:
        logger.error(f"Error in help_cmd: {e}")
        await message.answer("Error showing help")

# Fallback handler for unrecognized messages
@dp.message(F.text)
async def echo(message: types.Message):
    # Save conversation to memory
    try:
        save_message_with_analysis(message.from_user.id, message.text)
    except Exception as e:
        logger.error(f"Error saving conversation: {e}")
    
    lang = detect_lang(message.from_user.language_code)
    await message.answer(LANG[lang].get("help", "Use /help to see available commands"))

async def main():
    try:
        # Initialize database
        init_db()
        logger.info("Database initialized")
        
        logger.info("Starting bot...")
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Critical error in main: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
