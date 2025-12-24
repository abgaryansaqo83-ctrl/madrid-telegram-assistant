# backend/events.py

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import psycopg  # ensure psycopg is in requirements.txt

logger = logging.getLogger(__name__)

# ENV variable with DSN of the DB (կարող է լինել նույն DATABASE_URL-ը)
EVENTS_DB_URL = os.getenv("EVENTS_DB_URL") or os.getenv("DATABASE_URL")

Event = Dict[str, str]


def _get_conn():
    """
    Բացում է նոր PostgreSQL connection.
    EVENTS_DB_URL օրինակ:
      postgres://user:password@host:port/dbname
    """
    if not EVENTS_DB_URL:
        raise RuntimeError("EVENTS_DB_URL is not set (or DATABASE_URL missing)")
    return psycopg.connect(EVENTS_DB_URL)


def init_events_schema() -> None:
    """
    Ստեղծում է madrid_events աղյուսակը, եթե դեռ չկա.
    Կարող ես կանչել բոտի start-ի ժամանակ կամ առանձին migration script-ով.
    """
    sql = """
    CREATE TABLE IF NOT EXISTS madrid_events (
        id          SERIAL PRIMARY KEY,
        category    VARCHAR(32) NOT NULL,   -- cinema, restaurant, holiday
        title       TEXT NOT NULL,
        place       TEXT,
        start_time  TIMESTAMPTZ NOT NULL,
        end_time    TIMESTAMPTZ,
        city        TEXT NOT NULL DEFAULT 'Madrid',
        link        TEXT,
        extra       JSONB,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    CREATE INDEX IF NOT EXISTS idx_madrid_events_category_time
        ON madrid_events (category, start_time);

    CREATE UNIQUE INDEX IF NOT EXISTS uniq_madrid_events_identity
        ON madrid_events (category, title, place, start_time);
    """
    try:
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql)
        logger.info("madrid_events table ensured/initialized")
    except Exception as e:
        logger.error(f"Error initializing madrid_events schema: {e}", exc_info=True)
        raise


def upsert_event(
    category: str,
    title: str,
    place: str,
    start_time: datetime,
    end_time: Optional[datetime] = None,
    city: str = "Madrid",
    link: Optional[str] = None,
    extra: Optional[Dict] = None,
) -> None:
    """
    Գրանցում/թարմացնում է event-ը, նույնացնողը (category, title, place, start_time).

    Սա կօգտագործեն scrapers-ը կամ քո մանուալ loader սկրիպտները,
    ոչ թե հենց Telegram բոտի հանդլերները։
    """
    sql = """
    INSERT INTO madrid_events
        (category, title, place, start_time, end_time, city, link, extra)
    VALUES
        (%(category)s, %(title)s, %(place)s, %(start_time)s, %(end_time)s,
         %(city)s, %(link)s, %(extra)s)
    ON CONFLICT (category, title, place, start_time)
    DO UPDATE SET
        end_time   = EXCLUDED.end_time,
        city       = EXCLUDED.city,
        link       = EXCLUDED.link,
        extra      = EXCLUDED.extra,
        updated_at = now();
    """

    params = {
        "category": category,
        "title": title,
        "place": place,
        "start_time": start_time,
        "end_time": end_time,
        "city": city,
        "link": link,
        "extra": extra,
    }

    try:
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
        logger.debug("Madrid event upserted: %s — %s", category, title)
    except Exception as e:
        logger.error(f"Error upserting Madrid event '{title}': {e}", exc_info=True)
        raise


def _fetch_upcoming_events(category: str, limit: int = 3) -> List[Event]:
    """
    Վերցնում է random events-ներ տրված category-ի համար։
    Եթե այսօրվա events-ներ չկան, վերցնում է մոտակա 3 օրվա events-ները։
    """
    from datetime import date
    
    today = date.today().isoformat()
    next_3_days = (date.today() + timedelta(days=3)).isoformat()
    
    # Փորձիր գտնել այսօրվա events-ներ
    sql_today = """
    SELECT title, place, start_time, source_url
    FROM madrid_events
    WHERE category = %(category)s
      AND date = %(today)s
    ORDER BY RANDOM()
    LIMIT %(limit)s;
    """
    
    params_today = {
        "category": category,
        "today": today,
        "limit": limit,
    }
    
    try:
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql_today, params_today)
            rows = cur.fetchall()
            
            # Եթե այսօրվա events-ներ չկան, վերցրու մոտակա 3 օրվա
            if not rows:
                sql_upcoming = """
                SELECT title, place, start_time, source_url
                FROM madrid_events
                WHERE category = %(category)s
                  AND date BETWEEN %(today)s AND %(next_3_days)s
                ORDER BY RANDOM()
                LIMIT %(limit)s;
                """
                
                params_upcoming = {
                    "category": category,
                    "today": today,
                    "next_3_days": next_3_days,
                    "limit": limit,
                }
                
                cur.execute(sql_upcoming, params_upcoming)
                rows = cur.fetchall()
    
    except Exception as e:
        logger.error(
            f"Error fetching madrid_events for category='{category}': {e}",
            exc_info=True,
        )
        return []

    events: List[Event] = []
    for title, place, start_time, source_url in rows:
        events.append(
            {
                "title": title,
                "place": place or "",
                "time": start_time or "",
                "link": source_url or "",
            }
        )
    return events


def get_upcoming_cinema_events(limit: int = 3) -> List[Event]:
    """
    Առաջիկա 🎬 cinema event-ներ Մադրիդում.
    """
    return _fetch_upcoming_events("cinema", limit=limit)

def get_upcoming_theatre_events(limit: int = 3) -> List[Event]:
    """
    Առաջիկա 🎭 թատրոնի event-ներ Մադրիդում.
    """
    return _fetch_upcoming_events("theatre", limit=limit)


def get_upcoming_restaurant_events(limit: int = 3) -> List[Event]:
    """
    Առաջիկա 🍽 ռեստորանային / բարային event-ներ.
    """
    return _fetch_upcoming_events("restaurant", limit=limit)


def get_upcoming_holiday_events(limit: int = 3) -> List[Event]:
    """
    Առաջիկա 🎉 քաղաքային տոնական event-ներ (Christmas, ՆԳ, փառատոններ...).
    """
    return _fetch_upcoming_events("holiday", limit=limit)
