# backend/scheduler.py

import asyncio
import logging
from datetime import time, datetime, timedelta
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from backend.ai.traffic import madrid_morning_traffic

logger = logging.getLogger(__name__)

MADRID_GROUP_ID = -1003433432009
MADRID_TZ = pytz.timezone('Europe/Madrid')
scheduler = AsyncIOScheduler(timezone=MADRID_TZ)

async def send_morning_news(bot: Bot):
    try:
        from backend.news import format_morning_news

        news_text = format_morning_news()
        traffic_report = madrid_morning_traffic()
        full_text = (
            "Доброе утро! 👋\nСегодняшняя погода и дорожная ситуация:\n\n"
            f"{news_text}\n\n"
            f"{traffic_report}\n\n"
            "Желаем отличного дня в Мадриде! ☀️"
        )
        await bot.send_message(MADRID_GROUP_ID, full_text, parse_mode="HTML")
        logger.info(f"Morning news sent to group {MADRID_GROUP_ID}")

    except Exception as e:
        logger.error(f"Error sending morning news: {e}")

def start_scheduler(bot: Bot):
    try:
        scheduler.remove_all_jobs()
        scheduler.add_job(
            send_morning_news,
            CronTrigger(hour=8, minute=30, timezone=MADRID_TZ),
            args=[bot],
            id='morning_news_job',
            name='Send morning news at 8:30 AM Madrid time'
        )
        if not scheduler.running:
            scheduler.start()
            logger.info("Scheduler started successfully")
        logger.info("Morning news job scheduled for 8:30 AM Madrid time (CET/CEST)")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")

def stop_scheduler():
    try:
        if scheduler.running:
            scheduler.shutdown()
            logger.info("Scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
