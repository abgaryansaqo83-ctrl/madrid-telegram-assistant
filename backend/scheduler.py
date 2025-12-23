# backend/scheduler.py
# ==========================
#  IMPORTS & SETUP
# ==========================
import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.events_sources_madrid import refresh_madrid_events_for_today
from apscheduler.triggers.cron import CronTrigger
import pytz

from backend.news import (
    build_city_overview_message,
    build_cinema_message,
    build_restaurant_message,
    build_holidays_message,
)
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
    Առավոտյան news digest մեկ կամ մի քանի մեսիջով.
    Կազմում է overview + кино + рестораны + праздники + трафик.
    """
    try:
        parts = []

        overview = build_city_overview_message()
        if overview:
            parts.append(overview)

        cinema = build_cinema_message(max_items=3)
        if cinema:
            parts.append(cinema)

        restaurants = build_restaurant_message(max_items=3)
        if restaurants:
            parts.append(restaurants)

        holidays = build_holidays_message(max_items=3)
        if holidays:
            parts.append(holidays)

        traffic_msgs = madrid_morning_traffic()
        if traffic_msgs:
            parts.extend(traffic_msgs)


        if not parts:
            logger.info("No morning messages to send")
            return

        # Կարող ես կամ ամեն մասը առանձին մեսիջով ուղարկել,
        # կամ մեկ մեծ տեքստով՝ "\n\n".join(parts)
        for text in parts:
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
    Սկսում է scheduler-ը և գրանցում job-երը.
    """
    try:
        if not scheduler.running:
            # Առավոտվա digest՝ 8:30
            scheduler.add_job(
                send_morning_news,
                CronTrigger(hour=8, minute=30),
                args=[bot],
                id="morning_news",
                replace_existing=True,
            )

            # Գիշերային refresh madrid_events-ի համար՝ 03:00
            scheduler.add_job(
                refresh_madrid_events_for_today,
                CronTrigger(hour=3, minute=0),
                id="refresh_madrid_events",
                replace_existing=True,
            )

            scheduler.start()
            logger.info("✅ Scheduler started (8:30 digest, 03:00 refresh)")
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
