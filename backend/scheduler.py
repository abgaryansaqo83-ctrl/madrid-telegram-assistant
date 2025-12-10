# backend/scheduler.py
# ==========================
#  IMPORTS & SETUP
# ==========================
import asyncio
import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from backend.news import build_morning_event_messages
from backend.ai.traffic import madrid_morning_traffic

logger = logging.getLogger(__name__)

MADRID_GROUP_ID = -1003433432009  # Madrid group/chat ID
MADRID_TZ = pytz.timezone("Europe/Madrid")

scheduler = AsyncIOScheduler(timezone=MADRID_TZ)


# ==========================
#  MORNING DIGEST JOB
# ==========================
async def send_morning_news(bot: Bot):
    """
    Առավոտյան news digest՝ մի քանի մեսիջներով:
    1) Обзор дня
    2) Кино
    3) Рестораны
    4) Праздники
    + traffic բլոկ backend.ai.traffic-ից
    """
    try:
        messages = build_morning_event_messages()
        # traffic-ից messages list (եթե դատարկ չէ)
        traffic_msgs = madrid_morning_traffic()
        if traffic_msgs:
            messages.extend(traffic_msgs)

        if not messages:
            logger.info("No morning messages to send")
            return

        for text in messages:
            if not text:
                continue
            await bot.send_message(
                MADRID_GROUP_ID,
                text,
                disable_web_page_preview=True,
            )

        logger.info("✅ Morning digest sent")

    except Exception as e:
        logger.error("❌ Morning news error: %s", e, exc_info=True)


# ==========================
#  SCHEDULER CONTROL
# ==========================
def start_scheduler(bot: Bot):
    """
    Սկսում է scheduler-ը և գրանցում առավոտյան job-ը (8:30 Madrid time).
    """
    try:
        if not scheduler.running:
            scheduler.add_job(
                send_morning_news,
                CronTrigger(hour=8, minute=30),
                args=[bot],
                id="morning_news",
                replace_existing=True,
            )
            scheduler.start()
            logger.info("✅ Scheduler started (8:30 Madrid)")
        else:
            logger.info("Scheduler already running")
    except Exception as e:
        logger.error("❌ Scheduler error: %s", e, exc_info=True)


def stop_scheduler():
    """
    Անջատում է scheduler-ը (օգտակար shutdown-ի ժամանակ).
    """
    try:
        if scheduler.running:
            scheduler.shutdown()
            logger.info("✅ Scheduler stopped")
    except Exception as e:
        logger.error("❌ Stop scheduler error: %s", e, exc_info=True)
