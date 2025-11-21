# backend/scheduler.py

import asyncio
import logging
from datetime import time, datetime, timedelta
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz  # NEW IMPORT

logger = logging.getLogger(__name__)

# Group chat ID for morning news
MADRID_GROUP_ID = -1003433432009

# Madrid timezone
MADRID_TZ = pytz.timezone('Europe/Madrid')

scheduler = AsyncIOScheduler(timezone=MADRID_TZ)

async def send_morning_news(bot: Bot):
    """
    Send morning news at 8:30 AM Madrid time
    Weather (real data) + Traffic (casual)
    Russian language
    """
    try:
        from backend.news import format_morning_news
        
        news_text = format_morning_news()
        await bot.send_message(MADRID_GROUP_ID, news_text, parse_mode="HTML")
        logger.info(f"Morning news sent to group {MADRID_GROUP_ID}")
        
    except Exception as e:
        logger.error(f"Error sending morning news: {e}")

def start_scheduler(bot: Bot):
    """
    Start the scheduler for daily morning news
    """
    try:
        # Remove existing jobs if any
        scheduler.remove_all_jobs()
        
        # Add job: send morning news every day at 8:30 AM Madrid time
        scheduler.add_job(
            send_morning_news,
            CronTrigger(hour=8, minute=30, timezone=MADRID_TZ),
            args=[bot],
            id='morning_news_job',
            name='Send morning news at 8:30 AM Madrid time'
        )
        
        # Start scheduler if not running
        if not scheduler.running:
            scheduler.start()
            logger.info("Scheduler started successfully")
        
        logger.info("Morning news job scheduled for 8:30 AM Madrid time (CET/CEST)")
        
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")

def stop_scheduler():
    """
    Stop the scheduler
    """
    try:
        if scheduler.running:
            scheduler.shutdown()
            logger.info("Scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
