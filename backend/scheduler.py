# backend/scheduler.py - ՊԱՏՐԱՍՏ ԴԵՊԼՈՅԻ
import asyncio
import logging
from datetime import time
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from backend.news import build_morning_event_messages
from backend.ai.traffic import madrid_morning_traffic

logger = logging.getLogger(__name__)

MADRID_GROUP_ID = -1003433432009  # քո Madrid group ID
MADRID_TZ = pytz.timezone('Europe/Madrid')
scheduler = AsyncIOScheduler(timezone=MADRID_TZ)

async def send_morning_news(bot: Bot):
    """Առավոտյան news digest"""
    try:
        messages = build_morning_event_messages()
        messages.extend(madrid_morning_traffic())
        
        for text in messages:
            await bot.send_message(MADRID_GROUP_ID, text, disable_web_page_preview=True)
        logger.info("✅ Morning digest sent")
    except Exception as e:
        logger.error(f"❌ Morning news error: {e}", exc_info=True)

def start_scheduler(bot: Bot):
    """Scheduler start"""
    try:
        if not scheduler.running:
            scheduler.add_job(send_morning_news, CronTrigger(hour=8, minute=30), args=[bot], id="morning_news")
            scheduler.start()
            logger.info("✅ Scheduler started (8:30 Madrid)")
    except Exception as e:
        logger.error(f"❌ Scheduler error: {e}")

def stop_scheduler():
    """Scheduler stop"""
    try:
        if scheduler.running:
            scheduler.shutdown()
            logger.info("✅ Scheduler stopped")
    except Exception as e:
        logger.error(f"❌ Stop scheduler error: {e}")
