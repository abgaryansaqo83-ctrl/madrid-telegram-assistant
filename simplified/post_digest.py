# simplified/post_digest.py

import os
import logging
from datetime import datetime
from typing import List
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from dotenv import load_dotenv

# ՆՈՐ IMPORT-ՆԵՐ NEWS-Ի ՀԱՄԱՐ
from backend.news import (
    build_city_overview_message,
    build_cinema_message,
    build_restaurant_message,
    build_holidays_message,
)
from backend.jobs import get_last_posted_items, save_posted_item

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
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


async def post_digest() -> None:
    """
    Կարճ առավոտյան digest միայն Մադրիդի event-ներով.
    1) Общий обзор города
    2) 🎬 Кино и развлечения
    3) 🍽 События в ресторанах
    4) 🎉 Праздники в Мадриде
    Ամեն բլոկը առանձին մեսիջ է, political news չի ուղարկվում։
    """
    try:
        last_posted: set = get_last_posted_items()
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M")

        # 1. Общий обзор города
        try:
            overview = build_city_overview_message()
        except Exception as e:
            logger.error(f"Error building city overview: {e}", exc_info=True)
            overview = ""

        if overview:
            header = f"📬 Madrid Digest — {now_str}\n\n"
            text = header + overview
            if len(text) > MAX_MESSAGE_LENGTH:
                text = text[: MAX_MESSAGE_LENGTH - 50] + "\n\n... (truncated)"
            try:
                await bot.send_message(
                    CHAT_ID,
                    text,
                    disable_web_page_preview=True,
                )
                logger.info("✅ Overview message posted")
            except TelegramAPIError as e:
                logger.error(f"Telegram API error (overview): {e}")

        # 2. Кино и развлечения
        try:
            cinema_text = build_cinema_message(max_items=3)
        except Exception as e:
            logger.error(f"Error building cinema block: {e}", exc_info=True)
            cinema_text = ""

        if cinema_text:
            if len(cinema_text) > MAX_MESSAGE_LENGTH:
                cinema_text = cinema_text[: MAX_MESSAGE_LENGTH - 50] + "\n\n... (truncated)"
            try:
                await bot.send_message(
                    CHAT_ID,
                    cinema_text,
                    disable_web_page_preview=True,
                )
                logger.info("✅ Cinema message posted")
            except TelegramAPIError as e:
                logger.error(f"Telegram API error (cinema): {e}")

        # 3. События в ресторанах
        try:
            rest_text = build_restaurant_message(max_items=3)
        except Exception as e:
            logger.error(f"Error building restaurant block: {e}", exc_info=True)
            rest_text = ""

        if rest_text:
            if len(rest_text) > MAX_MESSAGE_LENGTH:
                rest_text = rest_text[: MAX_MESSAGE_LENGTH - 50] + "\n\n... (truncated)"
            try:
                await bot.send_message(
                    CHAT_ID,
                    rest_text,
                    disable_web_page_preview=True,
                )
                logger.info("✅ Restaurant message posted")
            except TelegramAPIError as e:
                logger.error(f"Telegram API error (restaurants): {e}")

        # 4. Праздники в Мадриде
        try:
            holidays_text = build_holidays_message(max_items=3)
        except Exception as e:
            logger.error(f"Error building holidays block: {e}", exc_info=True)
            holidays_text = ""

        if holidays_text:
            if len(holidays_text) > MAX_MESSAGE_LENGTH:
                holidays_text = holidays_text[: MAX_MESSAGE_LENGTH - 50] + "\n\n... (truncated)"
            try:
                await bot.send_message(
                    CHAT_ID,
                    holidays_text,
                    disable_web_page_preview=True,
                )
                logger.info("✅ Holidays message posted")
            except TelegramAPIError as e:
                logger.error(f"Telegram API error (holidays): {e}")

        # posted_items logic-ը հիմա գրեթե չի օգտագործվում,
        # բայց թողնում ենք, որ հետո, եթե ուզես, կարողանաս
        #
