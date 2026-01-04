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
from backend.events import get_upcoming_cinema_events
from backend.ai.traffic import madrid_morning_traffic

logger = logging.getLogger(__name__)

# 📌 Madrid Telegram group/chat ID
CHAT_ID = -1003433432009  # override env-ով եթե պետք լինի

# 📌 Madrid time zone
MADRID_TZ = pytz.timezone("Europe/Madrid")

# 📌 APScheduler instance
scheduler = AsyncIOScheduler(timezone=MADRID_TZ)


# ==========================
#  MORNING DIGEST JOB
# ==========================
async def send_morning_news(bot: Bot):
    try:
        # 1) Header որպես text
        header = "📬 *Обзор дня в Мадриде*"
        await bot.send_message(
            chat_id=CHAT_ID,
            text=header,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )

        # 2) Կինո՝ նույն քարտերով, ինչ «🎬 Кино / Cine» մենյուում
        events = get_upcoming_cinema_events(limit=2)

        for e in events:
            title = (e.get("title") or "").strip()
            place = (e.get("place") or "").strip()
            address = (e.get("address") or "").strip()
            url = (e.get("url") or "").strip()
            image_url = (e.get("image_url") or "").strip()

            # հասցեն բաժանում ենք, որ չկտրվի
            address_lines = []
            if address:
                parts = [p.strip() for p in address.split(",") if p.strip()]
                if parts:
                    address_lines.append(f"📍 {parts[0]}")
                    if len(parts) > 1:
                        rest = ", ".join(parts[1:])
                        address_lines.append(f"📍 {rest}")

            lines = []
            if title:
                lines.append(f"*{title}*")
            if place:
                lines.append(f"📍 {place}")
            lines.extend(address_lines)
            if url:
                lines.append(f"🔗 [Подробнее]({url})")

            caption = "\n".join(lines) if lines else "🎬 Кино"

            if image_url:
                await bot.send_photo(
                    chat_id=CHAT_ID,
                    photo=image_url,
                    caption=caption,
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                )
            else:
                await bot.send_message(
                    chat_id=CHAT_ID,
                    text=caption,
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                )

    except Exception as e:
        logger.error(f"Morning news error: {e}", exc_info=True)

        # 3. Рестораны и бары (մինչև 2 event)
        try:
            restaurants = build_restaurant_message(max_items=2)
        except Exception as e:
            logger.error("Error building restaurant block: %s", e, exc_info=True)
            restaurants = ""

        if restaurants:
            parts.append(restaurants)

        # 4. Праздники и городские мероприятия (մինչև 2 event)
        try:
            holidays = build_holidays_message(max_items=2)
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

        for text in parts:
            await bot.send_message(
                CHAT_ID,
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
