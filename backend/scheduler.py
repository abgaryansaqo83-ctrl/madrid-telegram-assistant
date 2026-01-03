# backend/scheduler.py

import logging
import pytz

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.news import (
    build_city_overview_message,
    build_cinema_message,
    build_restaurant_message,
    build_holidays_message,
)
from backend.ai.traffic import madrid_morning_traffic

logger = logging.getLogger(__name__)

# 📌 Madrid Telegram group/chat ID
MADRID_GROUP_ID = -1003433432009  # override env-ով եթե պետք լինի

# 📌 Madrid time zone
MADRID_TZ = pytz.timezone("Europe/Madrid")

# 📌 APScheduler instance
scheduler = AsyncIOScheduler(timezone=MADRID_TZ)


# ==========================
#  MORNING DIGEST JOB
# ==========================
async def send_morning_news(bot: Bot):
    """
    Առավոտյան news digest Մադրիդի համար.
    Կազմում է մի քանի մեսիջով.
      1) Общий обзор дня
      2) Кино и развлечения
      3) События в ресторанах
      4) Праздники и городские мероприятия
      5) Утренний трафик (если есть данные)
    Ամբողջը ռուսերեն, հետո կարելի է ավելացնել իսպաներեն բլոկներ։
    """
    try:
        parts = []

        # 1. Обзор города
        try:
            overview = build_city_overview_message()
        except Exception as e:
            logger.error("Error building city overview: %s", e, exc_info=True)
            overview = ""

        if overview:
            overview = "📬 *Обзор дня в Мадриде*"
            parts.append(overview)

        # 2. Кино и развлечения
        try:
            cinema = build_cinema_message(max_items=3)
        except Exception as e:
            logger.error("Error building cinema block: %s", e, exc_info=True)
            cinema = ""

        if cinema:
            parts.append(cinema)

        # 3. Рестораны и бары
        try:
            restaurants = build_restaurant_message(max_items=3)
        except Exception as e:
            logger.error("Error building restaurant block: %s", e, exc_info=True)
            restaurants = ""

        if restaurants:
            parts.append(restaurants)

        # 4. Праздники и городские мероприятия
        try:
            holidays = build_holidays_message(max_items=3)
        except Exception as e:
            logger.error("Error building holidays block: %s", e, exc_info=True)
            holidays = ""

        if holidays:
            parts.append(holidays)

        # 5. Утренний трафик
        try:
            traffic_msgs = madrid_morning_traffic()
        except Exception as e:
            logger.error("Error building traffic messages: %s", e, exc_info=True)
            traffic_msgs = []

        if traffic_msgs:
            parts.extend(traffic_msgs)

        if not parts:
            logger.info("No morning messages to send (all blocks empty)")
            return

        # Ուղարկում ենք հերթով, Markdown parse_mode-ով
        for text in parts:
            await bot.send_message(
                MADRID_GROUP_ID,
                text,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )

        logger.info("✅ Morning digest sent (%d messages)", len(parts))

    except Exception as e:
        logger.error("❌ Morning news error: %s", e, exc_info=True)


# ==========================
#  SCHEDULER CONTROL
# ==========================
def start_scheduler(bot: Bot):
    """
    Սկսում է scheduler-ը և գրանցում job-երը.
    Հիմա.
      - Առավոտվա digest՝ ամեն օր 08:30 Madrid ժամանակով
      - Կլցնենք նաև գիշերային refresh մադրիդյան event-ների համար, եթե պետք է
    """
    try:
        if scheduler.running:
            logger.info("Scheduler already running")
            return

        # Առավոտվա digest՝ 08:30 Europe/Madrid
        scheduler.add_job(
            send_morning_news,
            CronTrigger(hour=8, minute=30),
            args=[bot],
            id="morning_news",
            replace_existing=True,
        )

        # Եթե ունես refresh_madrid_events_for_today, կարող ես պահել նաև սա.
        from backend.events_sources_madrid import refresh_madrid_events_for_today

        scheduler.add_job(
            refresh_madrid_events_for_today,
            CronTrigger(hour=3, minute=0),
            id="refresh_madrid_events",
            replace_existing=True,
        )

        scheduler.start()
        logger.info("✅ Scheduler started (08:30 digest, 03:00 refresh)")

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
