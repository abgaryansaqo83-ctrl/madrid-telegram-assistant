# backend/scheduler.py

import logging
import pytz
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.news import build_morning_event_messages

logger = logging.getLogger(__name__)

MADRID_GROUP_ID = -1003433432009
MADRID_TZ = pytz.timezone("Europe/Madrid")
scheduler = AsyncIOScheduler(timezone=MADRID_TZ)


async def send_morning_news(bot: Bot):
    """
    Ուղարկում է առավոտյան event‑ային digest՝ մի քանի մեսիջով:
    """
    try:
        texts = build_morning_event_messages()  # ցուցակ str‑երի
        if not texts:
            logger.info("No morning event messages to send")
            return

        for text in texts:
            # Կարող ես օգտագործել Markdown կամ HTML՝ ըստ backend.news‑ի ձևաչափի
            await bot.send_message(
                MADRID_GROUP_ID,
                text,
                disable_web_page_preview=True,
            )
        logger.info(f"Morning news sent to group {MADRID_GROUP_ID}")
    except Exception as e:
        logger.error(f"Error sending morning news: {e}", exc_info=True)


def start_scheduler(bot: Bot):
    """
    Կանչիր main()‑ում՝ բոտի стартից առաջ:
    """
    try:
        scheduler.remove_all_jobs()
        scheduler.add_job(
            send_morning_news,
            CronTrigger(hour=8, minute=30, timezone=MADRID_TZ),
            args=[bot],
            id="morning_news_job",
            name="Send morning news at 8:30 AM Madrid time",
        )
        if not scheduler.running:
            scheduler.start()
            logger.info("Scheduler started successfully")
        logger.info("Morning news job scheduled for 8:30 AM Madrid time (CET/CEST)")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}", exc_info=True)


def stop_scheduler():
    try:
        if scheduler.running:
            scheduler.shutdown()
            logger.info("Scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}", exc_info=True)
